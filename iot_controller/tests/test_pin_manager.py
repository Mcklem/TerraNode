import unittest
from core.pin_manager import PinConflictError, PinManager


class TestPinManager(unittest.TestCase):

    def setUp(self):
        self.pm = PinManager()

    def test_valid_pin_allocation(self):
        devices_cfg = {
            "dev_01": {"node": "node_01", "pin": "D5"},
            "dev_02": {"node": "node_01", "pin": "D6"},
            "dev_03": {"node": "node_01", "bus": "i2c", "address": "0x77"},
            "dev_04": {"node": "node_01", "bus": "i2c", "address": 0x76},
        }
        # Should not raise exception
        self.pm.validate_all(devices_cfg)

    def test_pin_conflict_raises_error(self):
        devices_cfg = {
            "soil_sensor_01": {"node": "irrigation_01", "pin": "A0"},
            "soil_sensor_02": {"node": "irrigation_01", "pin": "A0"},
        }
        with self.assertRaises(PinConflictError):
            self.pm.validate_all(devices_cfg)

    def test_i2c_address_conflict_raises_error(self):
        devices_cfg = {
            "bmp180_a": {"node": "weather_01", "bus": "i2c", "address": "0x77"},
            "bmp180_b": {"node": "weather_01", "bus": "i2c", "address": "0x77"},
        }
        with self.assertRaises(PinConflictError):
            self.pm.validate_all(devices_cfg)


if __name__ == "__main__":
    unittest.main()
