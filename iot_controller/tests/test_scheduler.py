import asyncio
import unittest
from core.device_manager import DeviceManager
from core.event_bus import EventBus
from core.node_manager import NodeManager
from core.pin_manager import PinManager
from core.scheduler import Scheduler


class TestScheduler(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.nm = NodeManager()
        self.pm = PinManager()
        self.dm = DeviceManager(self.nm, self.pm)
        self.bus = EventBus()

        node = self.nm.create_node("n1", {"driver": "mock", "host": "127.0.0.1"})
        await node.connect()

        self.dm.initialize_devices({
            "s1": {"type": "ldr", "node": "n1", "pin": "A0", "poll_interval": 1}
        })
        await self.dm.start_all()
        self.scheduler = Scheduler(self.dm, self.bus)

    async def test_scheduler_polling(self):
        events = []

        def _on_event(event):
            events.append(event)

        self.bus.subscribe("device.value_changed", _on_event)

        await self.scheduler.start()
        await asyncio.sleep(1.2)
        await self.scheduler.stop()

        self.assertGreaterEqual(len(events), 1)
        self.assertEqual(events[0].sender, "s1")


if __name__ == "__main__":
    unittest.main()
