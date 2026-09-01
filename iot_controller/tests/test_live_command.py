import asyncio
import time
import unittest
from automation.rule_engine import RuleEngine
from core.device_manager import DeviceManager
from core.event_bus import EventBus
from core.node_manager import NodeManager
from core.pin_manager import PinManager
from devices.actuators.relay import RelayActuator
from services.live_command import (
    CommandDispatcher,
    ControlMode,
    LiveCommandService,
    OverrideRegistry,
)


class TestLiveCommandService(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.nm = NodeManager()
        self.pm = PinManager()
        self.dm = DeviceManager(self.nm, self.pm)
        self.bus = EventBus()

        node = self.nm.create_node("n1", {"driver": "mock", "host": "127.0.0.1"})
        await node.connect()

        self.dm.initialize_devices({
            "soil_01": {"type": "soil_moisture", "node": "n1", "pin": "A0"},
            "pump_01": {"type": "relay", "node": "n1", "pin": "D5"},
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

        rules_cfg = {
            "irrigation_stop": {
                "enabled": True,
                "condition": {"device": "soil_01", "property": "value", "operator": ">", "value": 70},
                "actions": [{"device": "pump_01", "command": "turn_off"}],
            }
        }
        self.engine = RuleEngine(
            rules_cfg,
            self.dm,
            self.bus,
            command_dispatcher=self.dispatcher,
        )
        self.engine.start()

    async def test_live_command_executes_and_sets_override_mode(self):
        pump: RelayActuator = self.dm.get_device("pump_01")
        self.assertEqual(pump.current_state, "OFF")

        # Execute manual ON
        res = await self.live_service.execute_live_command("pump_01", "turn_on")
        self.assertTrue(res.success)
        self.assertEqual(pump.current_state, "ON")
        self.assertEqual(res.current_mode, ControlMode.MANUAL_ON)

        st = self.live_service.get_control_state("pump_01")
        self.assertTrue(st.is_override_active())
        self.assertEqual(st.mode, ControlMode.MANUAL_ON)

    async def test_rule_engine_action_blocked_when_override_active(self):
        pump: RelayActuator = self.dm.get_device("pump_01")

        # Set manual ON (Override)
        await self.live_service.execute_live_command("pump_01", "turn_on")
        self.assertEqual(pump.current_state, "ON")

        # Fire sensor event that matches rule (soil_moisture > 70 -> turn_off pump_01)
        await self.bus.publish(
            "device.value_changed",
            sender="soil_01",
            payload={"id": "soil_01", "value": 85.0, "status": "OK"},
        )

        # Pump MUST REMAIN ON because MANUAL_ON override blocks the rule command
        self.assertEqual(pump.current_state, "ON")
        st = self.live_service.get_control_state("pump_01")
        self.assertEqual(st.mode, ControlMode.MANUAL_ON)

    async def test_restore_control_resets_mode_to_auto(self):
        pump: RelayActuator = self.dm.get_device("pump_01")

        # Set manual ON
        await self.live_service.execute_live_command("pump_01", "turn_on")
        self.assertEqual(pump.current_state, "ON")

        # Restore control to AUTO
        res = await self.live_service.restore_control("pump_01")
        self.assertTrue(res.success)
        self.assertEqual(res.current_mode, ControlMode.AUTO)

        # Now rule should execute turn_off
        await self.bus.publish(
            "device.value_changed",
            sender="soil_01",
            payload={"id": "soil_01", "value": 85.0, "status": "OK"},
        )
        self.assertEqual(pump.current_state, "OFF")

    async def test_override_ttl_expiration(self):
        pump: RelayActuator = self.dm.get_device("pump_01")

        # Set manual ON with 0.1 sec TTL
        await self.live_service.execute_live_command("pump_01", "turn_on", ttl_seconds=0.1)
        self.assertEqual(pump.current_state, "ON")

        await asyncio.sleep(0.15)

        # TTL expired -> state reverts to AUTO
        st = self.live_service.get_control_state("pump_01")
        self.assertFalse(st.is_override_active())
        self.assertEqual(st.mode, ControlMode.AUTO)

    async def test_raw_node_command(self):
        # Execute raw node digital write
        res = await self.live_service.execute_raw_node_command("n1", "digital_write", "D5", 1)
        self.assertEqual(res["node_id"], "n1")
        self.assertEqual(res["pin"], "D5")
        self.assertEqual(res["value"], 1)


if __name__ == "__main__":
    unittest.main()
