import asyncio
import time
from typing import Optional, Union
from pymata4 import pymata4

from utils.logging import get_logger
from .base_node import BaseNode, NodeStatus, parse_pin

# Safe monkey-patch for Pymata4 to prevent IndexError on early ESP8266 analog packets
_orig_analog_message = pymata4.Pymata4._analog_message


def _safe_analog_message(self, data):
    if data and hasattr(self, "analog_pins"):
        pin = data[0]
        if pin < len(self.analog_pins):
            try:
                _orig_analog_message(self, data)
            except (IndexError, AttributeError):
                pass


pymata4.Pymata4._analog_message = _safe_analog_message


class FirmataNode(BaseNode):
    """Pymata4 / StandardFirmataWiFi node implementation."""

    def __init__(self, node_id: str, driver: str, host: str, port: int = 3030, enabled: bool = True, **kwargs):
        super().__init__(node_id, driver, host, port, enabled, **kwargs)
        self._board: Optional[pymata4.Pymata4] = None
        self._logger = get_logger("FirmataNode", node_id=self.id)
        self._i2c_initialized = False

    async def connect(self) -> bool:
        if not self.enabled:
            self._logger.info(f"Node {self.id} is disabled. Skipping connection.")
            return False

        max_retries = self.max_retries
        for attempt in range(1, max_retries + 1):
            self._logger.info(f"Connecting to NodeMCU at {self.host}:{self.port} (attempt {attempt}/{max_retries})...")
            start_time = time.time()

            def _init_board():
                return pymata4.Pymata4(
                    ip_address=self.host,
                    ip_port=self.port,
                    arduino_wait=self.arduino_wait,
                    shutdown_on_exception=False,
                )

            try:
                loop = asyncio.get_running_loop()
                self._board = await asyncio.wait_for(
                    loop.run_in_executor(None, _init_board),
                    timeout=self.timeout
                )
                self._latency_ms = (time.time() - start_time) * 1000
                self._mark_connected()
                self._logger.info(f"Successfully connected to Node {self.id} (latency: {self._latency_ms:.1f}ms).")
                return True
            except Exception as e:
                err_msg = f"Connection attempt {attempt} failed for {self.id} ({self.host}:{self.port}): {e}"
                self._logger.warning(err_msg)
                if self._board:
                    try:
                        self._board.shutdown()
                    except Exception:
                        pass
                    self._board = None

                if attempt < max_retries:
                    await asyncio.sleep(1.5)
                else:
                    self._mark_disconnected(reason=err_msg)
                    return False
        return False

    async def disconnect(self) -> None:
        if self._board:
            self._logger.info(f"Disconnecting Node {self.id}...")
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self._board.shutdown)
            except Exception as e:
                self._logger.warning(f"Error shutting down board for {self.id}: {e}")
            finally:
                self._board = None
                self._i2c_initialized = False
        self._mark_disconnected(reason="Explicit disconnect")

    async def reconnect(self) -> bool:
        self._reconnect_count += 1
        self._status = NodeStatus.RECONNECTING
        self._logger.info(f"Attempting reconnection {self._reconnect_count} for Node {self.id}...")
        await self.disconnect()
        await asyncio.sleep(1.0)
        return await self.connect()

    def set_pin_mode_digital_output(self, pin: Union[str, int]) -> None:
        pin_num = parse_pin(pin)
        if self._board:
            self._board.set_pin_mode_digital_output(pin_num)

    def set_pin_mode_digital_input(self, pin: Union[str, int], callback=None) -> None:
        pin_num = parse_pin(pin)
        if self._board:
            self._board.set_pin_mode_digital_input(pin_num, callback=callback)

    def set_pin_mode_analog_input(self, pin: Union[str, int], callback=None) -> None:
        pin_num = parse_pin(pin)
        if self._board:
            self._board.set_pin_mode_analog_input(pin_num, callback=callback)

    def set_pin_mode_servo(self, pin: Union[str, int], min_pulse: int = 544, max_pulse: int = 2400) -> None:
        pin_num = parse_pin(pin)
        if self._board:
            self._board.set_pin_mode_servo(pin_num, min_pulse=min_pulse, max_pulse=max_pulse)

    def set_pin_mode_i2c(self) -> None:
        if self._board and not self._i2c_initialized:
            self._board.set_pin_mode_i2c()
            self._i2c_initialized = True

    def digital_write(self, pin: Union[str, int], value: int) -> None:
        pin_num = parse_pin(pin)
        if self._board:
            self._board.digital_write(pin_num, 1 if value else 0)

    def digital_read(self, pin: Union[str, int]) -> int:
        pin_num = parse_pin(pin)
        if self._board:
            res = self._board.digital_read(pin_num)
            return res[0] if res else 0
        return 0

    def analog_read(self, pin: Union[str, int]) -> int:
        pin_num = parse_pin(pin)
        if self._board:
            res = self._board.analog_read(pin_num)
            return res[0] if res else 0
        return 0

    def servo_write(self, pin: Union[str, int], angle: int) -> None:
        pin_num = parse_pin(pin)
        if self._board:
            self._board.servo_write(pin_num, angle)

    async def i2c_write(self, address: int, data: list) -> None:
        if self._board:
            self.set_pin_mode_i2c()
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._board.i2c_write, address, data)

    async def i2c_read(self, address: int, register: int, num_bytes: int, timeout: float = 2.0) -> list:
        if not self._board:
            raise RuntimeError(f"Node {self.id} board is not connected.")

        self.set_pin_mode_i2c()

        event = asyncio.Event()
        result_raw = []
        loop = asyncio.get_running_loop()

        def _i2c_cb(data):
            nonlocal result_raw
            # pymata4 callback format: [pin_type(6), address, register, raw_byte0, raw_byte1, ..., timestamp]
            if len(data) >= 4 and data[1] == address and data[2] == register:
                raw_bytes = data[3:-1] if isinstance(data[-1], float) else data[3:]
                if len(raw_bytes) >= num_bytes:
                    result_raw = list(raw_bytes[:num_bytes])
                    loop.call_soon_threadsafe(event.set)

        self._board.i2c_read(address, register, num_bytes, callback=_i2c_cb)

        # Ensure pymata4 updates callback for this address in its internal map
        if hasattr(self._board, "i2c_map") and address in self._board.i2c_map:
            with self._board.the_i2c_map_lock:
                self._board.i2c_map[address]["callback"] = _i2c_cb

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            return result_raw
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"Node {self.id}: Timeout reading I2C address 0x{address:02X} register 0x{register:02X}"
            )
