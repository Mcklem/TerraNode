import time
from typing import Any, Dict
from devices.base_device import DeviceStatus
from devices.sensor import Sensor
from nodes.base_node import BaseNode


class SoilMoistureSensor(Sensor):
    """Soil moisture analog sensor driver with dry/wet calibration support."""

    def __init__(self, device_id: str, device_type: str, node: BaseNode, config: Dict[str, Any]):
        super().__init__(device_id, device_type, node, config)
        self.pin = config.get("pin", "A0")
        self.unit = "%"
        calibration = config.get("calibration", {})
        self.dry_val = calibration.get("dry", 900)
        self.wet_val = calibration.get("wet", 350)

    async def start(self) -> None:
        try:
            self.node.set_pin_mode_analog_input(self.pin)
            self.set_status(DeviceStatus.OK)
            self._logger.info(
                f"Soil Moisture Sensor initialized on pin {self.pin} (dry: {self.dry_val}, wet: {self.wet_val})"
            )
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
            # Map raw value to 0..100% moisture
            if self.dry_val != self.wet_val:
                pct = 100.0 * (self.dry_val - raw_val) / (self.dry_val - self.wet_val)
            else:
                pct = 0.0

            pct = max(0.0, min(100.0, pct))
            self._last_value = round(pct, 1)
            self._last_timestamp = time.time()
            self.set_status(DeviceStatus.OK)
        except Exception as e:
            self.set_status(DeviceStatus.ERROR, error=f"Error reading Soil Moisture sensor: {e}")

        return self.get_state()
