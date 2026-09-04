import asyncio
from typing import Dict, List, Optional
from nodes.base_node import BaseNode, NodeDriver, NodeStatus
from nodes.firmata_node import FirmataNode
from nodes.secure_firmata_node import SecureFirmataNode
from nodes.mock_node import MockNode
from utils.logging import get_logger


class NodeManager:
    """Manages the lifecycle, pool, and connectivity of hardware nodes."""

    def __init__(self):
        self._nodes: Dict[str, BaseNode] = {}
        self._logger = get_logger("NodeManager")

    def create_node(self, node_id: str, node_cfg: dict) -> BaseNode:
        """Instantiate node from config dictionary."""
        driver_raw = node_cfg.get("driver", NodeDriver.STANDARD_FIRMATA_WIFI.value).lower().strip()
        host = node_cfg.get("host", "127.0.0.1")
        port = node_cfg.get("port", 3030)
        enabled = node_cfg.get("enabled", True)

        from core.settings import settings

        arduino_wait = node_cfg.get("arduino_wait", settings.node_arduino_wait)
        max_retries = node_cfg.get("max_retries", settings.node_max_retries)
        timeout = float(node_cfg.get("timeout", settings.node_timeout))
        auth_key = node_cfg.get("auth_key")
        use_tls = node_cfg.get("use_tls", False)

        kwargs = {
            "node_id": node_id,
            "driver": driver_raw,
            "host": host,
            "port": port,
            "enabled": enabled,
            "arduino_wait": arduino_wait,
            "max_retries": max_retries,
            "timeout": timeout,
        }

        if driver_raw in (
            NodeDriver.STANDARD_FIRMATA_WIFI.value,
            NodeDriver.STANDARD_FIRMATA.value,
            NodeDriver.FIRMATA.value,
        ):
            node = FirmataNode(**kwargs)
        elif driver_raw in (
            NodeDriver.SECURE_STANDARD_FIRMATA_WIFI.value,
            NodeDriver.SECURE_FIRMATA.value,
        ):
            node = SecureFirmataNode(auth_key=auth_key, use_tls=use_tls, **kwargs)
        elif driver_raw == NodeDriver.MOCK.value:
            node = MockNode(**kwargs)
        else:
            raise ValueError(f"Unsupported node driver '{driver_raw}' for node '{node_id}'")

        self._nodes[node_id] = node
        return node

    def get_node(self, node_id: str) -> Optional[BaseNode]:
        return self._nodes.get(node_id)

    def get_all_nodes(self) -> List[BaseNode]:
        return list(self._nodes.values())

    async def connect_all(self) -> None:
        """Connect all enabled nodes concurrently."""
        tasks = []
        for node_id, node in self._nodes.items():
            if node.enabled:
                tasks.append(node.connect())
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def disconnect_all(self) -> None:
        """Disconnect all nodes gracefully."""
        tasks = [node.disconnect() for node in self._nodes.values()]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def health_report(self) -> Dict[str, dict]:
        return {node_id: node.health() for node_id, node in self._nodes.items()}
