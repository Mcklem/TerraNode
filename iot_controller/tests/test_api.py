import os
import tempfile
import unittest
from fastapi.testclient import TestClient
from api.app import create_app
from api.dependencies import system_container
from core.device_manager import DeviceManager
from core.event_bus import EventBus
from core.node_manager import NodeManager
from core.pin_manager import PinManager
from monitoring.health import HealthMonitor
from services.live_command import CommandDispatcher, LiveCommandService, OverrideRegistry
from storage.database import (
    ActuatorHistoryModel,
    Database,
    EventModel,
    MeasurementModel,
    NodeHistoryModel,
    ScheduleHistoryModel,
)


class TestFastAPIWebService(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self.temp_dir.name, "test.db")
        self.db = Database(database_url=self.db_path)
        await self.db.initialize()

        self.nm = NodeManager()
        self.pm = PinManager()
        self.dm = DeviceManager(self.nm, self.pm)

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
        )
        self.live_service = LiveCommandService(
            device_manager=self.dm,
            node_manager=self.nm,
            override_registry=self.override_reg,
            dispatcher=self.dispatcher,
        )
        self.bus = EventBus()
        self.health_mon = HealthMonitor(self.nm, self.dm, self.bus)

        # Inject dependencies into system_container
        system_container.device_manager = self.dm
        system_container.node_manager = self.nm
        system_container.health_monitor = self.health_mon
        system_container.live_command_service = self.live_service
        system_container.override_registry = self.override_reg
        system_container.db = self.db

        app = create_app()
        self.client = TestClient(app)

    async def asyncTearDown(self):
        await self.dm.stop_all()
        await self.nm.disconnect_all()
        self.db.close()
        self.temp_dir.cleanup()

    def test_health_endpoints(self):
        resp = self.client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "OK")
        self.assertEqual(data["total_nodes"], 1)

    def test_list_nodes_and_details(self):
        resp = self.client.get("/api/v1/nodes")
        self.assertEqual(resp.status_code, 200)
        nodes = resp.json()
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["id"], "n1")

        detail = self.client.get("/api/v1/nodes/n1")
        self.assertEqual(detail.status_code, 200)
        self.assertTrue(detail.json()["connected"])

    def test_list_devices_and_get_device(self):
        resp = self.client.get("/api/v1/devices")
        self.assertEqual(resp.status_code, 200)
        devs = resp.json()
        self.assertEqual(len(devs), 2)

        pump_info = self.client.get("/api/v1/devices/pump_01")
        self.assertEqual(pump_info.status_code, 200)
        self.assertEqual(pump_info.json()["control_mode"], "AUTO")

    def test_device_live_command_and_override_list(self):
        # 1. Check no active overrides initially
        overrides_before = self.client.get("/api/v1/overrides").json()
        self.assertEqual(len(overrides_before), 0)

        # 2. Execute live turn_on command on pump_01
        cmd_resp = self.client.post(
            "/api/v1/devices/pump_01/command",
            json={"action": "turn_on", "user_id": "TEST_USER"},
        )
        self.assertEqual(cmd_resp.status_code, 200)
        payload = cmd_resp.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["current_mode"], "MANUAL_ON")

        # 3. Verify override is listed in /api/v1/overrides
        overrides_after = self.client.get("/api/v1/overrides").json()
        self.assertEqual(len(overrides_after), 1)
        self.assertEqual(overrides_after[0]["device_id"], "pump_01")
        self.assertEqual(overrides_after[0]["mode"], "MANUAL_ON")

        # 4. Restore control back to AUTO
        restore_resp = self.client.post("/api/v1/devices/pump_01/restore-control")
        self.assertEqual(restore_resp.status_code, 200)
        self.assertEqual(restore_resp.json()["current_mode"], "AUTO")

        overrides_final = self.client.get("/api/v1/overrides").json()
        self.assertEqual(len(overrides_final), 0)

    def test_wrapped_payload_and_alias_commands(self):
        # Test wrapped Swagger UI format payload
        wrapped_json = {
            "summary": "1. Encendido Manual de Relé",
            "description": "Ejecuta turn_on",
            "value": {
                "action": "on",
                "params": {},
                "target_mode": "MANUAL_ON",
                "user_id": "operador_sala_1"
            }
        }
        resp = self.client.post("/api/v1/devices/pump_01/command", json=wrapped_json)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["current_mode"], "MANUAL_ON")

        # Clean up
        self.client.post("/api/v1/devices/pump_01/restore-control")

    def test_raw_pin_command(self):
        # 1. Unallocated pin succeeds
        pin_resp = self.client.post(
            "/api/v1/nodes/n1/pin",
            json={"command_type": "digital_write", "pin": "D1", "value": 1},
        )
        self.assertEqual(pin_resp.status_code, 200)
        self.assertEqual(pin_resp.json()["status"], "success")

        # 2. Pin D5 reserved by pump_01 should return 400 conflict error when PinManager is present
        system_container.pin_manager = self.pm
        self.pm.validate_all({
            "soil_01": {"type": "soil_moisture", "node": "n1", "pin": "A0"},
            "pump_01": {"type": "relay", "node": "n1", "pin": "D5"},
        })
        conflict_resp = self.client.post(
            "/api/v1/nodes/n1/pin",
            json={"command_type": "digital_write", "pin": "D5", "value": 1},
        )
        self.assertEqual(conflict_resp.status_code, 400)
        self.assertIn("reserved by active device 'pump_01'", conflict_resp.json()["detail"])

    def test_delete_all_overrides(self):
        # Create 2 overrides
        self.client.post("/api/v1/devices/pump_01/command", json={"action": "turn_on"})
        overrides = self.client.get("/api/v1/overrides").json()
        self.assertEqual(len(overrides), 1)

        # Delete all overrides at once
        del_resp = self.client.delete("/api/v1/overrides")
        self.assertEqual(del_resp.status_code, 200)
        self.assertTrue(del_resp.json()["success"])
        self.assertEqual(del_resp.json()["restored_count"], 1)

        overrides_after = self.client.get("/api/v1/overrides").json()
        self.assertEqual(len(overrides_after), 0)

    def test_history_purge_endpoint(self):
        purge_resp = self.client.post("/api/v1/history/purge?retention_days=30")
        self.assertEqual(purge_resp.status_code, 200)
        self.assertTrue(purge_resp.json()["success"])
        self.assertEqual(purge_resp.json()["retention_days"], 30)


    async def test_history_paginated_endpoints(self):
        # Seed test database with records
        def _seed(session):
            m1 = MeasurementModel(timestamp=100.0, device_id="soil_01", value=45.0, unit="%", status="OK")
            m2 = MeasurementModel(timestamp=200.0, device_id="soil_01", value=50.0, unit="%", status="OK")
            m3 = MeasurementModel(timestamp=300.0, device_id="ldr_01", value=512.0, unit="raw", status="OK")
            session.add_all([m1, m2, m3])

            act1 = ActuatorHistoryModel(timestamp=150.0, device_id="pump_01", state="turn_on", source="LIVE_MANUAL", user_id="juan")
            session.add(act1)

            node1 = NodeHistoryModel(timestamp=50.0, node_id="n1", host="127.0.0.1", port=3030, driver="mock", event="CONNECTED")
            session.add(node1)

            evt1 = EventModel(timestamp=60.0, topic="rule.triggered", sender="RuleEngine", payload="{}")
            session.add(evt1)

            sch1 = ScheduleHistoryModel(
                timestamp=70.0,
                schedule_id="riego_matutino",
                device_id="pump_01",
                action="turn_on",
                event_type="TRIGGERED",
                duration=900.0,
                status="SUCCESS",
            )
            session.add(sch1)

        await self.db.run_in_session(_seed)

        # 1. Test /api/v1/history/measurements with filter and pagination
        resp_m = self.client.get("/api/v1/history/measurements?device_id=soil_01&limit=1&offset=0")
        self.assertEqual(resp_m.status_code, 200)
        data_m = resp_m.json()
        self.assertEqual(data_m["total"], 2)
        self.assertEqual(data_m["limit"], 1)
        self.assertEqual(len(data_m["data"]), 1)
        self.assertEqual(data_m["data"][0]["timestamp"], 200.0)  # Descending order

        # 2. Test /api/v1/history/actuators
        resp_a = self.client.get("/api/v1/history/actuators")
        self.assertEqual(resp_a.status_code, 200)
        data_a = resp_a.json()
        self.assertEqual(data_a["total"], 1)
        self.assertEqual(data_a["data"][0]["user_id"], "juan")

        # 3. Test /api/v1/history/nodes
        resp_n = self.client.get("/api/v1/history/nodes?node_id=n1")
        self.assertEqual(resp_n.status_code, 200)
        data_n = resp_n.json()
        self.assertEqual(data_n["total"], 1)
        self.assertEqual(data_n["data"][0]["event"], "CONNECTED")

        # 4. Test /api/v1/history/schedules
        resp_s = self.client.get("/api/v1/history/schedules?schedule_id=riego_matutino")
        self.assertEqual(resp_s.status_code, 200)
        data_s = resp_s.json()
        self.assertEqual(data_s["total"], 1)
        self.assertEqual(data_s["data"][0]["schedule_id"], "riego_matutino")
        self.assertEqual(data_s["data"][0]["duration"], 900.0)

        # 5. Test /api/v1/history/events
        resp_e = self.client.get("/api/v1/history/events?topic=rule.triggered")
        self.assertEqual(resp_e.status_code, 200)
        data_e = resp_e.json()
        self.assertEqual(data_e["total"], 1)
        self.assertEqual(data_e["data"][0]["sender"], "RuleEngine")


if __name__ == "__main__":
    unittest.main()
