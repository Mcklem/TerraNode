import asyncio
import time
from typing import Dict, List, Optional
from core.device_manager import DeviceManager
from core.event_bus import EventBus
from core.node_manager import NodeManager
from nodes.base_node import NodeStatus
from utils.logging import get_logger


class HealthMonitor:
    """Monitors system, node, and device health with automatic background reconnection."""

    def __init__(
        self,
        node_manager: NodeManager,
        device_manager: DeviceManager,
        event_bus: EventBus,
        check_interval: int = 15,
    ):
        self.node_manager = node_manager
        self.device_manager = device_manager
        self.event_bus = event_bus
        self.check_interval = check_interval
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._logger = get_logger("HealthMonitor")

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        self._logger.info(f"HealthMonitor started (check interval: {self.check_interval}s).")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._logger.info("HealthMonitor stopped.")

    async def _monitor_loop(self) -> None:
        while self._running:
            try:
                await self._check_nodes_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Error during health check cycle: {e}")

            try:
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break

    async def _check_nodes_health(self) -> None:
        nodes = self.node_manager.get_all_nodes()
        for node in nodes:
            if not node.enabled:
                continue

            if not node.is_connected() and node.status != NodeStatus.RECONNECTING:
                self._logger.warning(
                    f"Node '{node.id}' is disconnected ({node.status.value}). Triggering auto-reconnect..."
                )
                await self.event_bus.publish(
                    topic="node.status_changed",
                    sender=node.id,
                    payload={"status": NodeStatus.RECONNECTING.value, "reason": "HealthMonitor auto-reconnect"},
                )
                asyncio.create_task(self._attempt_node_reconnect(node))

    async def _attempt_node_reconnect(self, node) -> None:
        """Attempt non-blocking reconnection with backoff retry."""
        try:
            success = await node.reconnect()
            if success:
                self._logger.info(f"Node '{node.id}' successfully reconnected.")
                await self.event_bus.publish(
                    topic="node.status_changed",
                    sender=node.id,
                    payload={"status": NodeStatus.CONNECTED.value},
                )
                # Restart devices attached to this node
                for dev in self.device_manager.get_all_devices():
                    if dev.node.id == node.id:
                        await dev.start()
            else:
                self._logger.warning(f"Reconnection attempt failed for node '{node.id}'.")
        except Exception as e:
            self._logger.error(f"Exception during node reconnect for '{node.id}': {e}")

    def get_system_health(self) -> Dict[str, dict]:
        return {
            "nodes": self.node_manager.health_report(),
            "devices": {
                dev.id: {
                    "type": dev.type,
                    "node": dev.node.id,
                    "status": dev.status.value,
                }
                for dev in self.device_manager.get_all_devices()
            },
        }
