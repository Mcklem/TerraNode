import time
from abc import abstractmethod
from typing import Any, Dict, Optional
from .base_device import BaseDevice, DeviceStatus
from nodes.base_node import BaseNode


class Sensor(BaseDevice):
    """Abstract base class for sensor devices."""

    def __init__(self, device_id: str, device_type: str, node: BaseNode, config: Dict[str, Any]):
        super().__init__(device_id, device_type, node, config)
        self.poll_interval: int = config.get("poll_interval", 10)
        self.unit: str = config.get("unit", "")
        self._last_value: Optional[Any] = None
        self._last_timestamp: Optional[float] = None

    @abstractmethod
    async def read(self) -> Dict[str, Any]:
        """Perform sensor reading and return normalized state."""
        pass

    def get_state(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "node": self.node.id,
            "status": self.status.value,
            "value": self._last_value,
            "unit": self.unit,
            "timestamp": self._last_timestamp or time.time(),
        }
