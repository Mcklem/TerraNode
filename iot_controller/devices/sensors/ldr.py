import time
from typing import Any, Dict
from devices.base_device import DeviceStatus
from devices.sensor import Sensor
from nodes.base_node import BaseNode, parse_pin


class LDRSensor(Sensor):
    """LDR (Light Dependent Resistor) analog light sensor driver with optional calibration support."""

    def __init__(self, device_id: str, device_type: str, node: BaseNode, config: Dict[str, Any]):
        super().__init__(device_id, device_type, node, config)
        self.pin = config.get("pin", "A0")
        self.calibration = config.get("calibration", {})
        self.unit = config.get("unit", "%" if self.calibration else "raw")

    async def start(self) -> None:
        try:
            self.node.set_pin_mode_analog_input(self.pin)
            self.set_status(DeviceStatus.OK)
            self._logger.info(f"LDR Sensor initialized on pin {self.pin}")
        except Exception as e:
            self.set_status(DeviceStatus.ERROR, error=f"Failed to set pin mode: {e}")

    async def stop(self) -> None:
        pass

    async def read(self) -> Dict[str, Any]:
        if not self.node.is_connected():
            self.set_status(DeviceStatus.DISCONNECTED)
            return self.get_state()

        try:
            raw_val = self.node.analog_read(self.pin)
            self._last_value = raw_val

            # Apply calibration mapping if configured (e.g. dark: 1024, light: 100)
            if self.calibration and "dark" in self.calibration and "light" in self.calibration:
                dark = float(self.calibration["dark"])
                light = float(self.calibration["light"])
                if dark != light:
                    pct = max(0.0, min(100.0, ((raw_val - dark) / (light - dark)) * 100.0))
                    self._last_value = round(pct, 1)

            self._last_timestamp = time.time()
            self.set_status(DeviceStatus.OK)
        except Exception as e:
            self.set_status(DeviceStatus.ERROR, error=f"Error reading LDR sensor: {e}")

        return self.get_state()
