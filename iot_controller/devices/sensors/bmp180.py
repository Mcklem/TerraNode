import asyncio
import time
from typing import Any, Dict, Optional
from devices.base_device import DeviceStatus
from devices.sensor import Sensor
from nodes.base_node import BaseNode


def _signed16(msb: int, lsb: int) -> int:
    val = (msb << 8) | lsb
    return val - 65536 if val & 0x8000 else val


def _unsigned16(msb: int, lsb: int) -> int:
    return (msb << 8) | lsb


class BMP180Sensor(Sensor):
    """BMP180 I2C Temperature, Pressure and Altitude Sensor Driver."""

    BMP180_ADDR = 0x77
    REG_CONTROL = 0xF4
    REG_DATA = 0xF6
    REG_CALIB = 0xAA

    def __init__(self, device_id: str, device_type: str, node: BaseNode, config: Dict[str, Any]):
        super().__init__(device_id, device_type, node, config)
        self.address = config.get("address", self.BMP180_ADDR)
        self.oss = config.get("oss", 0)  # Oversampling setting (0..3)
        self.unit = "°C"
        self._calib: Optional[Dict[str, int]] = None
        self._last_pressure: Optional[float] = None
        self._last_altitude: Optional[float] = None

    async def start(self) -> None:
        try:
            self.node.set_pin_mode_i2c()
            await self._load_calibration()
            self.set_status(DeviceStatus.OK)
            self._logger.info(f"BMP180 Sensor initialized at I2C address 0x{self.address:02X}")
        except Exception as e:
            self.set_status(DeviceStatus.ERROR, error=f"Failed to initialize BMP180: {e}")

    async def stop(self) -> None:
        pass

    async def _load_calibration(self) -> None:
        raw = await self.node.i2c_read(self.address, self.REG_CALIB, 22, timeout=3.0)
        if len(raw) < 22:
            raise RuntimeError(f"Expected 22 calibration bytes from BMP180, got {len(raw)}")

        self._calib = {
            "AC1": _signed16(raw[0], raw[1]),
            "AC2": _signed16(raw[2], raw[3]),
            "AC3": _signed16(raw[4], raw[5]),
            "AC4": _unsigned16(raw[6], raw[7]),
            "AC5": _unsigned16(raw[8], raw[9]),
            "AC6": _unsigned16(raw[10], raw[11]),
            "B1": _signed16(raw[12], raw[13]),
            "B2": _signed16(raw[14], raw[15]),
            "MB": _signed16(raw[16], raw[17]),
            "MC": _signed16(raw[18], raw[19]),
            "MD": _signed16(raw[20], raw[21]),
        }

    async def read_raw_temperature(self) -> int:
        await self.node.i2c_write(self.address, [self.REG_CONTROL, 0x2E])
        await asyncio.sleep(0.01)
        raw = await self.node.i2c_read(self.address, self.REG_DATA, 2, timeout=2.0)
        if len(raw) < 2:
            raise RuntimeError("Timeout or insufficient data reading BMP180 temperature")
        return (raw[0] << 8) | raw[1]

    async def read_raw_pressure(self) -> int:
        cmd = 0x34 + (self.oss << 6)
        await self.node.i2c_write(self.address, [self.REG_CONTROL, cmd])
        delay = 0.005 if self.oss == 0 else (0.008 if self.oss == 1 else (0.014 if self.oss == 2 else 0.026))
        await asyncio.sleep(delay)
        raw = await self.node.i2c_read(self.address, self.REG_DATA, 3, timeout=2.0)
        if len(raw) < 3:
            raise RuntimeError("Timeout or insufficient data reading BMP180 pressure")
        return ((raw[0] << 16) | (raw[1] << 8) | raw[2]) >> (8 - self.oss)

    def calculate_values(self, UT: int, UP: int):
        c = self._calib
        if not c:
            raise RuntimeError("Calibration data not loaded")

        # Temperature
        X1 = ((UT - c["AC6"]) * c["AC5"]) / (2 ** 15)
        denom = X1 + c["MD"]
        X2 = (c["MC"] * (2 ** 11)) / denom if denom != 0 else 0
        B5 = X1 + X2
        temp = (B5 + 8) / 160.0

        # Pressure
        X1 = (B5 - 4000) * (c["B2"] / (2 ** 11))
        X2 = (c["AC2"] * (B5 - 4000)) / (2 ** 11)
        X3 = X1 + X2
        B3 = (((c["AC1"] * 4 + int(X3)) * (2 ** self.oss)) + 2) / 4

        X1 = c["AC3"] * B5 / (2 ** 13)
        X2 = (c["B1"] * (B5 * B5 / (2 ** 12))) / (2 ** 16)
        X3 = ((X1 + X2) + 2) / 4
        B4 = c["AC4"] * (X3 + 32768) / (2 ** 15)

        B7 = (UP - B3) * (50000 / (2 ** self.oss))
        if B4 != 0:
            if B7 < 0x80000000:
                p = (B7 * 2) / B4
            else:
                p = (B7 / B4) * 2
        else:
            p = 101325.0

        X1 = (p / (2 ** 8)) ** 2
        X1 = (X1 * 3038) / (2 ** 16)
        X2 = (-7357 * p) / (2 ** 16)
        pressure_pa = p + ((X1 + X2 + 3791) / (2 ** 4))

        # Altitude (m)
        altitude = 44330.0 * (1.0 - (pressure_pa / 101325.0) ** 0.19029495)

        return round(temp, 2), round(pressure_pa / 100.0, 2), round(altitude, 2)

    async def read(self) -> Dict[str, Any]:
        if not self.node.is_connected():
            self.set_status(DeviceStatus.DISCONNECTED)
            return self.get_state()

        try:
            if not self._calib:
                await self._load_calibration()

            UT = await self.read_raw_temperature()
            UP = await self.read_raw_pressure()
            temp, pressure_hpa, altitude_m = self.calculate_values(UT, UP)

            self._last_value = temp
            self._last_pressure = pressure_hpa
            self._last_altitude = altitude_m
            self._last_timestamp = time.time()
            self.set_status(DeviceStatus.OK)
        except Exception as e:
            self.set_status(DeviceStatus.ERROR, error=f"Error reading BMP180 sensor: {e}")

        return self.get_state()

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["temperature"] = self._last_value
        state["pressure"] = self._last_pressure
        state["altitude"] = self._last_altitude
        return state
