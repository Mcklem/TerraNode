import asyncio
import os
import tempfile
import unittest
from sqlalchemy import select
from core.event_bus import EventBus
from storage.database import Database, MeasurementModel
from storage.repositories import StorageManager


class TestStorage(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self.temp_dir.name, "test.db")
        self.db = Database(database_url=self.db_path)
        await self.db.initialize()
        self.bus = EventBus()
        self.sm = StorageManager(self.db, self.bus)
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


if __name__ == "__main__":
    unittest.main()
