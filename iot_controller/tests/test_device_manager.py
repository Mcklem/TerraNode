import unittest
from core.device_manager import DeviceManager
from core.node_manager import NodeManager
from core.pin_manager import PinManager
from devices.actuator import Actuator
from devices.sensor import Sensor


class TestDeviceManager(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.nm = NodeManager()
        self.pm = PinManager()
        self.dm = DeviceManager(self.nm, self.pm)

        self.node = self.nm.create_node("n1", {"driver": "mock", "host": "127.0.0.1"})
        await self.node.connect()

    async def test_initialize_devices(self):
        devices_cfg = {
            "light_01": {"type": "ldr", "node": "n1", "pin": "A0"},
            "pump_01": {"type": "relay", "node": "n1", "pin": "D5"},
        }

        self.dm.initialize_devices(devices_cfg)
        await self.dm.start_all()

        sensors = self.dm.get_sensors()
        actuators = self.dm.get_actuators()

        self.assertEqual(len(sensors), 1)
        self.assertEqual(len(actuators), 1)
        self.assertIsInstance(sensors[0], Sensor)
        self.assertIsInstance(actuators[0], Actuator)

        await self.dm.stop_all()


if __name__ == "__main__":
    unittest.main()
