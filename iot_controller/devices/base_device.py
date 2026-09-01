from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional
from nodes.base_node import BaseNode, NodeStatus
from utils.logging import get_logger


class DeviceStatus(str, Enum):
    INITIALIZING = "INITIALIZING"
    OK = "OK"
    WARNING = "WARNING"
    ERROR = "ERROR"
    DISCONNECTED = "DISCONNECTED"


class BaseDevice(ABC):
    """Abstract base class for all physical hardware devices attached to nodes."""

    def __init__(self, device_id: str, device_type: str, node: BaseNode, config: Dict[str, Any]):
        self.id = device_id
        self.type = device_type
        self.node = node
        self.config = config
        self._status = DeviceStatus.INITIALIZING
        self._last_error: Optional[str] = None
        self._logger = get_logger(self.__class__.__name__, node_id=node.id, device_id=device_id)

    @property
    def status(self) -> DeviceStatus:
        if not self.node.is_connected():
            return DeviceStatus.DISCONNECTED
        return self._status

    def set_status(self, status: DeviceStatus, error: Optional[str] = None) -> None:
        self._status = status
        if error:
            self._last_error = error
            self._logger.error(f"Device status -> {status.value}: {error}")
        else:
            self._logger.debug(f"Device status -> {status.value}")

    @abstractmethod
    async def start(self) -> None:
        """Initialize pin modes and hardware registers on start."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Safe teardown on stop."""
        pass

    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """Return standardized device state dictionary."""
        pass
