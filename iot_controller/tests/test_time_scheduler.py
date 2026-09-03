import asyncio
import datetime
import os
import tempfile
import unittest
from fastapi.testclient import TestClient
from api.app import create_app
from api.dependencies import system_container
from automation.time_scheduler import TimeScheduler, match_cron, match_cron_field
from core.device_manager import DeviceManager
from core.event_bus import EventBus
from core.node_manager import NodeManager
from core.pin_manager import PinManager
from devices.actuators.relay import RelayActuator
from services.live_command.command_dispatcher import CommandDispatcher
from services.live_command.live_command_service import LiveCommandService
from services.live_command.override_registry import OverrideRegistry


class TestTimeScheduler(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.nm = NodeManager()
        self.pm = PinManager()
        self.dm = DeviceManager(self.nm, self.pm)
        self.bus = EventBus()

        node = self.nm.create_node("n1", {"driver": "mock", "host": "127.0.0.1"})
        await node.connect()

        self.dm.initialize_devices({
            "pump_01": {"type": "relay", "node": "n1", "pin": "D5", "active_low": True},
            "vent_servo": {"type": "servo", "node": "n1", "pin": "D7"},
        })
        await self.dm.start_all()

        self.override_reg = OverrideRegistry()
        self.dispatcher = CommandDispatcher(
            device_manager=self.dm,
            override_registry=self.override_reg,
            event_bus=self.bus,
        )
        self.live_service = LiveCommandService(
            device_manager=self.dm,
            node_manager=self.nm,
            override_registry=self.override_reg,
            dispatcher=self.dispatcher,
        )

        self.schedules_cfg = {
            "irrigation_job": {
                "enabled": True,
                "device": "pump_01",
                "command": "turn_on",
                "stop_command": "turn_off",
                "duration": 0.2,  # 0.2 seconds duration for fast testing
                "interval": 0.5,
            },
            "ventilation_job": {
                "enabled": True,
                "device": "vent_servo",
                "command": "set_position",
                "args": {"target_angle": 180},
                "stop_command": "set_position",
                "stop_args": {"target_angle": 0},
                "duration": 0.2,
                "interval": 10.0,
            },
        }

        self.time_scheduler = TimeScheduler(
            self.schedules_cfg,
            self.dm,
            self.bus,
            self.dispatcher,
        )
        self.time_scheduler.start()

        system_container.device_manager = self.dm
        system_container.node_manager = self.nm
        system_container.live_command_service = self.live_service
        system_container.override_registry = self.override_reg
        system_container.time_scheduler = self.time_scheduler

        app = create_app()
        self.client = TestClient(app)

    async def asyncTearDown(self):
        self.time_scheduler.stop()
        await self.dm.stop_all()
        await self.nm.disconnect_all()

    def test_cron_matcher(self):
        dt = datetime.datetime(2026, 9, 3, 8, 0, 0)  # Thursday 08:00 AM
        self.assertTrue(match_cron("* * * * *", dt))
        self.assertTrue(match_cron("0 8 * * *", dt))
        self.assertTrue(match_cron("0 8 * * 4", dt))  # Thursday
        self.assertFalse(match_cron("0 9 * * *", dt))
        self.assertFalse(match_cron("15 8 * * *", dt))

    async def test_trigger_schedule_with_duration_timer(self):
        pump: RelayActuator = self.dm.get_device("pump_01")
        self.assertEqual(pump.current_state, "OFF")

        # Trigger irrigation job manually
        success = await self.time_scheduler.trigger_schedule("irrigation_job")
        self.assertTrue(success)
        self.assertEqual(pump.current_state, "ON")

        # Wait for duration timer (0.2s) to expire
        await asyncio.sleep(0.35)
        self.assertEqual(pump.current_state, "OFF")

    async def test_schedule_blocked_when_override_active(self):
        pump: RelayActuator = self.dm.get_device("pump_01")

        # Set manual OFF override on pump_01
        await self.live_service.execute_live_command("pump_01", "turn_off")
        self.assertEqual(pump.current_state, "OFF")

        # Try to trigger irrigation_job (which sends turn_on)
        success = await self.time_scheduler.trigger_schedule("irrigation_job")
        self.assertFalse(success)  # Blocked by override!
        self.assertEqual(pump.current_state, "OFF")

    async def test_run_on_start_interval(self):
        start_cfg = {
            "start_job": {
                "enabled": True,
                "device": "pump_01",
                "command": "turn_on",
                "interval": 3600.0,
                "run_on_start": True,
            }
        }
        sched = TimeScheduler(start_cfg, self.dm, self.bus, self.dispatcher)
        sched.start()
        try:
            await asyncio.sleep(0.15)
            pump: RelayActuator = self.dm.get_device("pump_01")
            self.assertEqual(pump.current_state, "ON")
        finally:
            sched.stop()

    def test_api_schedules_list_and_trigger(self):
        # GET /api/v1/schedules
        resp = self.client.get("/api/v1/schedules")
        self.assertEqual(resp.status_code, 200)
        schedules = resp.json()
        self.assertEqual(len(schedules), 2)

        # GET /api/v1/schedules/irrigation_job (Detail)
        detail_resp = self.client.get("/api/v1/schedules/irrigation_job")
        self.assertEqual(detail_resp.status_code, 200)
        self.assertEqual(detail_resp.json()["device"], "pump_01")
        self.assertEqual(detail_resp.json()["command"], "turn_on")

        # POST /api/v1/schedules/irrigation_job/trigger
        trig_resp = self.client.post("/api/v1/schedules/irrigation_job/trigger")
        self.assertEqual(trig_resp.status_code, 200)
        self.assertTrue(trig_resp.json()["success"])

        # POST /api/v1/schedules/irrigation_job/toggle
        tog_resp = self.client.post("/api/v1/schedules/irrigation_job/toggle")
        self.assertEqual(tog_resp.status_code, 200)
        self.assertFalse(tog_resp.json()["enabled"])


if __name__ == "__main__":
    unittest.main()
