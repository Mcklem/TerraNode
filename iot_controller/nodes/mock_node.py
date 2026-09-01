import asyncio
from typing import Dict, List, Optional, Union

from utils.logging import get_logger
from .base_node import BaseNode, NodeStatus, parse_pin


class MockNode(BaseNode):
    """Simulated node for offline testing and hardware-free execution."""

    def __init__(self, node_id: str, driver: str = "mock", host: str = "127.0.0.1", port: int = 3030, enabled: bool = True, **kwargs):
        super().__init__(node_id, driver, host, port, enabled, **kwargs)
        self.digital_pins: Dict[int, int] = {}
        self.analog_pins: Dict[int, int] = {}
        self.servo_positions: Dict[int, int] = {}
        self.pin_modes: Dict[int, str] = {}

        # Simulated I2C memory map: (address, register) -> list of bytes
        self.i2c_registers: Dict[tuple, list] = {
            (0x77, 0xAA): [
                0x1C, 0xB6, 0xFA, 0xB8, 0xC7, 0xBE, 0x80, 0x11,
                0x61, 0xC4, 0x58, 0x79, 0x18, 0x2A, 0x00, 0x25,
                0x80, 0x00, 0xD0, 0x0C, 0x0B, 0xFE
            ],
            (0x77, 0xF6): [0x77, 0xED, 0x00]
        }
        self.should_fail_connection: bool = False
        self._logger = get_logger("MockNode", node_id=self.id)

    async def connect(self) -> bool:
        if not self.enabled or self.should_fail_connection:
            self._mark_disconnected(reason="Simulated connection failure or disabled")
            return False
        self._mark_connected()
        self._latency_ms = 1.0
        self._logger.info(f"MockNode {self.id} connected successfully.")
        return True

    async def disconnect(self) -> None:
        self._mark_disconnected(reason="Mock disconnect")
        self._logger.info(f"MockNode {self.id} disconnected.")

    async def reconnect(self) -> bool:
        self._reconnect_count += 1
        self._status = NodeStatus.RECONNECTING
        await self.disconnect()
        await asyncio.sleep(0.01)
        return await self.connect()

    def set_pin_mode_digital_output(self, pin: Union[str, int]) -> None:
        pin_num = parse_pin(pin)
        self.pin_modes[pin_num] = "OUTPUT"

    def set_pin_mode_digital_input(self, pin: Union[str, int], callback=None) -> None:
        pin_num = parse_pin(pin)
        self.pin_modes[pin_num] = "INPUT"

    def set_pin_mode_analog_input(self, pin: Union[str, int], callback=None) -> None:
        pin_num = parse_pin(pin)
        self.pin_modes[pin_num] = "ANALOG_INPUT"

    def set_pin_mode_servo(self, pin: Union[str, int], min_pulse: int = 544, max_pulse: int = 2400) -> None:
        pin_num = parse_pin(pin)
        self.pin_modes[pin_num] = "SERVO"

    def set_pin_mode_i2c(self) -> None:
        self.pin_modes[-1] = "I2C"

    def digital_write(self, pin: Union[str, int], value: int) -> None:
        pin_num = parse_pin(pin)
        self.digital_pins[pin_num] = 1 if value else 0

    def digital_read(self, pin: Union[str, int]) -> int:
        pin_num = parse_pin(pin)
        return self.digital_pins.get(pin_num, 0)

    def analog_read(self, pin: Union[str, int]) -> int:
        pin_num = parse_pin(pin)
        return self.analog_pins.get(pin_num, 512)

    def analog_write(self, pin: Union[str, int], value: int) -> None:
        pin_num = parse_pin(pin)
        self.analog_pins[pin_num] = int(value)

    def servo_write(self, pin: Union[str, int], angle: int) -> None:
        pin_num = parse_pin(pin)
        self.servo_positions[pin_num] = angle

    def set_mock_analog_value(self, pin: Union[str, int], value: int) -> None:
        pin_num = parse_pin(pin)
        self.analog_pins[pin_num] = value

    def set_mock_i2c_data(self, address: int, register: int, data: list) -> None:
        self.i2c_registers[(address, register)] = list(data)

    async def i2c_write(self, address: int, data: list) -> None:
        if data:
            register = data[0]
            payload = data[1:]
            self.i2c_registers[(address, register)] = payload

    async def i2c_read(self, address: int, register: int, num_bytes: int, timeout: float = 2.0) -> list:
        key = (address, register)
        if key in self.i2c_registers:
            res = self.i2c_registers[key]
            if len(res) >= num_bytes:
                return res[:num_bytes]
            return res + [0] * (num_bytes - len(res))
        # Default mock bytes if uninitialized
        return [0] * num_bytes
