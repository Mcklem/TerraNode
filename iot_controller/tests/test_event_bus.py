import unittest
from core.event_bus import Event, EventBus


class TestEventBus(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.bus = EventBus()

    async def test_publish_subscribe(self):
        received_events = []

        def _handler(event: Event):
            received_events.append(event)

        self.bus.subscribe("device.value_changed", _handler)
        await self.bus.publish("device.value_changed", sender="sensor_1", payload={"val": 42})

        self.assertEqual(len(received_events), 1)
        self.assertEqual(received_events[0].sender, "sensor_1")
        self.assertEqual(received_events[0].payload["val"], 42)

    async def test_wildcard_subscription(self):
        received = []

        def _handler(event: Event):
            received.append(event.topic)

        self.bus.subscribe("device.*", _handler)
        await self.bus.publish("device.value_changed", sender="s1", payload={})
        await self.bus.publish("device.status_changed", sender="s1", payload={})
        await self.bus.publish("other.topic", sender="s1", payload={})

        self.assertEqual(len(received), 2)
        self.assertIn("device.value_changed", received)
        self.assertIn("device.status_changed", received)


if __name__ == "__main__":
    unittest.main()
