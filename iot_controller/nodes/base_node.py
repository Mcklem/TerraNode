import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional, Union


class NodeStatus(str, Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    RECONNECTING = "RECONNECTING"
    ERROR = "ERROR"


# NodeMCU pin mapping table
NODEMCU_PIN_MAP = {
    "D0": 16,
    "D1": 5,
    "D2": 4,
    "D3": 0,
    "D4": 2,
    "D5": 14,
    "D6": 12,
    "D7": 13,
    "D8": 15,
    "A0": 0,
}


def parse_pin(pin: Union[str, int]) -> int:
    """Parse a pin identifier into its numeric pin number."""
    if isinstance(pin, int):
        return pin
    if isinstance(pin, str):
        pin_str = pin.strip().upper()
        if pin_str in NODEMCU_PIN_MAP:
            return NODEMCU_PIN_MAP[pin_str]
        if pin_str.isdigit():
            return int(pin_str)
    raise ValueError(f"Invalid pin identifier: '{pin}'")


class BaseNode(ABC):
    """Abstract base class for all node hardware abstraction drivers."""

    def __init__(
        self,
        node_id: str,
        driver: str,
        host: str,
        port: int = 3030,
        enabled: bool = True,
        arduino_wait: int = 5,
        max_retries: int = 3,
        timeout: float = 12.0,
    ):
        self.id = node_id
        self.driver = driver
        self.host = host
        self.port = port
        self.enabled = enabled
        self.arduino_wait = arduino_wait
        self.max_retries = max_retries
        self.timeout = timeout

        self._status = NodeStatus.DISCONNECTED
        self._last_seen: Optional[float] = None
        self._connection_time: Optional[float] = None
        self._disconnect_count: int = 0
        self._reconnect_count: int = 0
        self._latency_ms: float = 0.0
        self._last_error: Optional[str] = None

    @property
    def status(self) -> NodeStatus:
        return self._status

    def is_connected(self) -> bool:
        return self._status == NodeStatus.CONNECTED

    def health(self) -> Dict[str, Any]:
        """Return standardized node health metrics."""
        return {
            "id": self.id,
            "status": self._status.value,
            "host": self.host,
            "port": self.port,
            "enabled": self.enabled,
            "last_seen": self._last_seen,
            "connection_time": self._connection_time,
            "disconnect_count": self._disconnect_count,
            "reconnect_count": self._reconnect_count,
            "latency_ms": round(self._latency_ms, 2),
            "last_error": self._last_error,
        }

    def _mark_connected(self) -> None:
        self._status = NodeStatus.CONNECTED
        now = time.time()
        self._last_seen = now
        if not self._connection_time:
            self._connection_time = now

    def _mark_disconnected(self, reason: Optional[str] = None) -> None:
        if self._status == NodeStatus.CONNECTED:
            self._disconnect_count += 1
        self._status = NodeStatus.DISCONNECTED
        if reason:
            self._last_error = reason

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the hardware node."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the hardware node gracefully."""
        pass

    @abstractmethod
    async def reconnect(self) -> bool:
        """Attempt reconnection to the node."""
        pass

    # High Level Hardware Abstraction API
    @abstractmethod
    def set_pin_mode_digital_output(self, pin: Union[str, int]) -> None:
        pass

    @abstractmethod
    def set_pin_mode_digital_input(self, pin: Union[str, int], callback=None) -> None:
        pass

    @abstractmethod
    def set_pin_mode_analog_input(self, pin: Union[str, int], callback=None) -> None:
        pass

    @abstractmethod
    def set_pin_mode_servo(self, pin: Union[str, int], min_pulse: int = 544, max_pulse: int = 2400) -> None:
        pass

    @abstractmethod
    def set_pin_mode_i2c(self) -> None:
        pass

    @abstractmethod
    def digital_write(self, pin: Union[str, int], value: int) -> None:
        pass

    @abstractmethod
    def digital_read(self, pin: Union[str, int]) -> int:
        pass

    @abstractmethod
    def analog_read(self, pin: Union[str, int]) -> int:
        pass

    @abstractmethod
    def servo_write(self, pin: Union[str, int], angle: int) -> None:
        pass

    @abstractmethod
    async def i2c_write(self, address: int, data: list) -> None:
        pass

    @abstractmethod
    async def i2c_read(self, address: int, register: int, num_bytes: int, timeout: float = 2.0) -> list:
        pass
