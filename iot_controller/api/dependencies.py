from typing import Optional
from core.device_manager import DeviceManager
from core.node_manager import NodeManager
from monitoring.health import HealthMonitor
from services.live_command import LiveCommandService, OverrideRegistry
from storage.database import Database


class SystemContainer:
    """Singleton-style container holding system references for FastAPI dependencies."""

    def __init__(self):
        self.device_manager: Optional[DeviceManager] = None
        self.node_manager: Optional[NodeManager] = None
        self.health_monitor: Optional[HealthMonitor] = None
        self.live_command_service: Optional[LiveCommandService] = None
        self.override_registry: Optional[OverrideRegistry] = None
        self.db: Optional[Database] = None


system_container = SystemContainer()


def get_device_manager() -> DeviceManager:
    if system_container.device_manager is None:
        raise RuntimeError("DeviceManager is not initialized in API container")
    return system_container.device_manager


def get_node_manager() -> NodeManager:
    if system_container.node_manager is None:
        raise RuntimeError("NodeManager is not initialized in API container")
    return system_container.node_manager


def get_health_monitor() -> Optional[HealthMonitor]:
    return system_container.health_monitor


def get_live_command_service() -> LiveCommandService:
    if system_container.live_command_service is None:
        raise RuntimeError("LiveCommandService is not initialized in API container")
    return system_container.live_command_service


def get_override_registry() -> OverrideRegistry:
    if system_container.override_registry is None:
        raise RuntimeError("OverrideRegistry is not initialized in API container")
    return system_container.override_registry


def get_database() -> Database:
    if system_container.db is None:
        raise RuntimeError("Database is not initialized in API container")
    return system_container.db
