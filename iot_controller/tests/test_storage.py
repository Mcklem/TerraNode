import asyncio
import os
import tempfile
import unittest
from sqlalchemy import select
from core.event_bus import EventBus
from core.node_manager import NodeManager
from storage.database import ActuatorHistoryModel, Database, MeasurementModel, NodeHistoryModel
from storage.repositories import StorageManager


class TestStorage(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self.temp_dir.name, "test.db")
        self.db = Database(database_url=self.db_path)
        await self.db.initialize()
        self.bus = EventBus()
        self.nm = NodeManager()
        node = self.nm.create_node("n1", {"driver": "mock", "host": "192.168.1.50", "port": 3030})
        await node.connect()

        self.sm = StorageManager(self.db, self.bus, node_manager=self.nm)
        self.sm.start()

    async def asyncTearDown(self):
        self.sm.stop()
        self.temp_dir.cleanup()

    async def test_measurement_logging_orm(self):
        await self.bus.publish(
            "device.value_changed",
            sender="ldr_1",
            payload={"id": "ldr_1", "value": 512, "unit": "raw", "status": "OK"},
        )

        await asyncio.sleep(0.1)

        def _query(session):
            stmt = select(MeasurementModel).where(MeasurementModel.device_id == "ldr_1")
            return session.scalars(stmt).all()

        measurements = await self.db.run_in_session(_query)
        self.assertEqual(len(measurements), 1)
        self.assertEqual(measurements[0].value, 512.0)
        self.assertEqual(measurements[0].unit, "raw")

    async def test_actuator_history_logging(self):
        await self.bus.publish(
            "command.executed",
            sender="CommandDispatcher",
            payload={
                "device_id": "pump_01",
                "action": "turn_on",
                "source": "LIVE_MANUAL",
                "user_id": "operador_juan",
            },
        )

        await asyncio.sleep(0.1)

        def _query(session):
            stmt = select(ActuatorHistoryModel).where(ActuatorHistoryModel.device_id == "pump_01")
            return session.scalars(stmt).all()

        history = await self.db.run_in_session(_query)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].state, "turn_on")
        self.assertEqual(history[0].source, "LIVE_MANUAL")
        self.assertEqual(history[0].user_id, "operador_juan")

    async def test_node_history_logging(self):
        await self.bus.publish(
            "node.status_changed",
            sender="n1",
            payload={"status": "CONNECTED"},
        )

        await asyncio.sleep(0.1)

        def _query(session):
            stmt = select(NodeHistoryModel).where(NodeHistoryModel.node_id == "n1")
            return session.scalars(stmt).all()

        node_logs = await self.db.run_in_session(_query)
        self.assertEqual(len(node_logs), 1)
        self.assertEqual(node_logs[0].host, "192.168.1.50")
        self.assertEqual(node_logs[0].port, 3030)
        self.assertEqual(node_logs[0].event, "CONNECTED")


if __name__ == "__main__":
    unittest.main()
