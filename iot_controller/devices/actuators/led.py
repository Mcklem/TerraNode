import time
from typing import Any, Dict
from devices.actuator import Actuator
from devices.base_device import DeviceStatus
from nodes.base_node import BaseNode


class LedActuator(Actuator):
    """LED digital actuator driver supporting active_high and active_low logic."""

    def __init__(self, device_id: str, device_type: str, node: BaseNode, config: Dict[str, Any]):
        super().__init__(device_id, device_type, node, config)
        self.pin = config.get("pin", "D0")
        self.active_low: bool = config.get("active_low", False)

    async def start(self) -> None:
        try:
            self.node.set_pin_mode_digital_output(self.pin)
            await self.turn_off()
            self.set_status(DeviceStatus.OK)
            self._logger.info(
                f"LED initialized on pin {self.pin} (active_low={self.active_low})"
            )
        except Exception as e:
            self.set_status(DeviceStatus.ERROR, error=f"Failed to initialize LED: {e}")

    async def stop(self) -> None:
        try:
            await self.turn_off()
        except Exception:
            pass

    async def turn_on(self) -> Dict[str, Any]:
        if not self.node.is_connected():
            self.set_status(DeviceStatus.DISCONNECTED)
            return self.get_state()

        try:
            write_val = 0 if self.active_low else 1
            self.node.digital_write(self.pin, write_val)
            self._current_state = "ON"
            self._last_timestamp = time.time()
            self.set_status(DeviceStatus.OK)
            self._logger.info(f"LED {self.id} -> ON")
        except Exception as e:
            self.set_status(DeviceStatus.ERROR, error=f"Error setting LED ON: {e}")

        return self.get_state()

    async def turn_off(self) -> Dict[str, Any]:
        if not self.node.is_connected():
            self.set_status(DeviceStatus.DISCONNECTED)
            return self.get_state()

        try:
            write_val = 1 if self.active_low else 0
            self.node.digital_write(self.pin, write_val)
            self._current_state = "OFF"
            self._last_timestamp = time.time()
            self.set_status(DeviceStatus.OK)
            self._logger.info(f"LED {self.id} -> OFF")
        except Exception as e:
            self.set_status(DeviceStatus.ERROR, error=f"Error setting LED OFF: {e}")

        return self.get_state()
