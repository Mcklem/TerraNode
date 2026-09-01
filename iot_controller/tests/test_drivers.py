import unittest
from devices.actuators.relay import RelayActuator
from devices.actuators.servo import ServoActuator
from devices.sensors.bmp180 import BMP180Sensor
from devices.sensors.ldr import LDRSensor
from devices.sensors.soil_moisture import SoilMoistureSensor
from nodes.mock_node import MockNode


class TestDrivers(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.node = MockNode("test_node")
        await self.node.connect()

    async def test_ldr_sensor(self):
        sensor = LDRSensor("ldr_1", "ldr", self.node, {"pin": "A0"})
        await sensor.start()

        self.node.set_mock_analog_value("A0", 750)
        state = await sensor.read()

        self.assertEqual(state["status"], "OK")
        self.assertEqual(state["value"], 750)

    async def test_soil_moisture_sensor_calibration(self):
        sensor = SoilMoistureSensor(
            "soil_1", "soil_moisture", self.node, {"pin": "A0", "calibration": {"dry": 1000, "wet": 200}}
        )
        await sensor.start()

        # At dry (1000) -> 0% moisture
        self.node.set_mock_analog_value("A0", 1000)
        state1 = await sensor.read()
        self.assertEqual(state1["value"], 0.0)

        # At wet (200) -> 100% moisture
        self.node.set_mock_analog_value("A0", 200)
        state2 = await sensor.read()
        self.assertEqual(state2["value"], 100.0)

        # At midpoint (600) -> 50% moisture
        self.node.set_mock_analog_value("A0", 600)
        state3 = await sensor.read()
        self.assertEqual(state3["value"], 50.0)

    async def test_relay_actuator_active_low(self):
        relay = RelayActuator("relay_1", "relay", self.node, {"pin": "D5", "active_low": True})
        await relay.start()

        await relay.turn_on()
        self.assertEqual(relay.current_state, "ON")
        # Active low write is 0
        self.assertEqual(self.node.digital_read("D5"), 0)

        await relay.turn_off()
        self.assertEqual(relay.current_state, "OFF")
        # Active low write is 1
        self.assertEqual(self.node.digital_read("D5"), 1)

    async def test_servo_actuator(self):
        servo = ServoActuator("servo_1", "servo", self.node, {"pin": "D6", "min_angle": 0, "max_angle": 180})
        await servo.start()

        await servo.set_position(90)
        self.assertEqual(servo.angle, 90)
        self.assertEqual(self.node.servo_positions[12], 90)  # D6 = GPIO12

        # Test angle clamping > 180
        await servo.set_position(200)
        self.assertEqual(servo.angle, 180)

    async def test_bmp180_sensor_with_mock_i2c(self):
        bmp = BMP180Sensor("bmp_1", "bmp180", self.node, {"address": 0x77})

        # Mock 22 calibration bytes for BMP180
        mock_calib_bytes = [
            0x1C, 0xB6,  # AC1 = 7350
            0xFA, 0xB8,  # AC2 = -1352
            0xC7, 0xBE,  # AC3 = -14402
            0x80, 0x11,  # AC4 = 32785
            0x61, 0xC4,  # AC5 = 25028
            0x58, 0x79,  # AC6 = 22649
            0x18, 0x2A,  # B1  = 6186
            0x00, 0x25,  # B2  = 37
            0x80, 0x00,  # MB  = -32768
            0xD0, 0x0C,  # MC  = -12276
            0x0B, 0xFE,  # MD  = 3070
        ]
        self.node.set_mock_i2c_data(0x77, 0xAA, mock_calib_bytes)
        # Mock raw temperature bytes
        self.node.set_mock_i2c_data(0x77, 0xF6, [0x77, 0xED, 0x00])

        await bmp.start()
        state = await bmp.read()

        self.assertEqual(state["status"], "OK")
        self.assertIsNotNone(state["value"])
        self.assertIn("pressure", state)
        self.assertIn("altitude", state)


if __name__ == "__main__":
    unittest.main()
