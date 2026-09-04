import time
from abc import abstractmethod
from typing import Any, Dict, Optional
from .base_device import BaseDevice
from nodes.base_node import BaseNode


class Actuator(BaseDevice):
    """Abstract base class for actuator devices."""

    def __init__(self, device_id: str, device_type: str, node: BaseNode, config: Dict[str, Any]):
        super().__init__(device_id, device_type, node, config)
        self._current_state: str = "OFF"
        self._last_timestamp: Optional[float] = None

    @property
    def current_state(self) -> str:
        return self._current_state

    @property
    def category(self) -> str:
        return "actuator"

    @abstractmethod
    async def turn_on(self) -> Dict[str, Any]:
        """Turn on the actuator."""
        pass

    @abstractmethod
    async def turn_off(self) -> Dict[str, Any]:
        """Turn off the actuator."""
        pass

    async def toggle(self) -> Dict[str, Any]:
        """Toggle actuator state."""
        if self._current_state == "ON":
            return await self.turn_off()
        else:
            return await self.turn_on()

    def get_state(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "node": self.node.id,
            "status": self.status.value,
            "state": self._current_state,
            "timestamp": self._last_timestamp or time.time(),
        }
