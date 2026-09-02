import time
from typing import Any, Dict
from devices.actuator import Actuator
from devices.base_device import DeviceStatus
from nodes.base_node import BaseNode


class ServoActuator(Actuator):
    """Servo PWM actuator driver with angle validation (0°..180°)."""

    def __init__(self, device_id: str, device_type: str, node: BaseNode, config: Dict[str, Any]):
        super().__init__(device_id, device_type, node, config)
        self.pin = config.get("pin", "D6")
        self.min_angle: int = config.get("min_angle", 0)
        self.max_angle: int = config.get("max_angle", 180)
        self.min_pulse: int = config.get("min_pulse", 544)
        self.max_pulse: int = config.get("max_pulse", 2400)
        self._current_angle: int = self.min_angle

    @property
    def angle(self) -> int:
        return self._current_angle

    async def start(self) -> None:
        try:
            self.node.set_pin_mode_servo(self.pin, min_pulse=self.min_pulse, max_pulse=self.max_pulse)
            await self.set_position(self.min_angle)
            self.set_status(DeviceStatus.OK)
            self._logger.info(
                f"Servo initialized on pin {self.pin} (min_angle={self.min_angle}, max_angle={self.max_angle})"
            )
        except Exception as e:
            self.set_status(DeviceStatus.ERROR, error=f"Failed to initialize Servo: {e}")

    async def stop(self) -> None:
        pass

    async def set_position(self, target_angle: Optional[int] = None, angle: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        if not self.node.is_connected():
            self.set_status(DeviceStatus.DISCONNECTED)
            return self.get_state()

        raw_angle = target_angle if target_angle is not None else angle
        if raw_angle is None:
            raw_angle = self.min_angle

        angle_val = max(self.min_angle, min(self.max_angle, int(raw_angle)))
        try:
            self.node.servo_write(self.pin, angle_val)
            self._current_angle = angle_val
            self._current_state = f"ANGLE_{angle_val}"
            self._last_timestamp = time.time()
            self.set_status(DeviceStatus.OK)
            self._logger.info(f"Servo {self.id} -> {angle_val}°")
        except Exception as e:
            self.set_status(DeviceStatus.ERROR, error=f"Error setting Servo position: {e}")

        return self.get_state()

    async def turn_on(self) -> Dict[str, Any]:
        """Turn on maps to maximum angle position."""
        return await self.set_position(self.max_angle)

    async def turn_off(self) -> Dict[str, Any]:
        """Turn off maps to minimum angle position."""
        return await self.set_position(self.min_angle)

    def get_state(self) -> Dict[str, Any]:
        state = super().get_state()
        state["angle"] = self._current_angle
        return state
