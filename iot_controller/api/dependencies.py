from typing import Any, Optional
from core.device_manager import DeviceManager
from core.node_manager import NodeManager
from core.pin_manager import PinManager
from monitoring.health import HealthMonitor
from services.live_command import LiveCommandService, OverrideRegistry
from storage.database import Database


class SystemContainer:
    """Singleton-style container holding system references for FastAPI dependencies."""

    def __init__(self):
        self.device_manager: Optional[DeviceManager] = None
        self.node_manager: Optional[NodeManager] = None
        self.pin_manager: Optional[PinManager] = None
        self.health_monitor: Optional[HealthMonitor] = None
        self.live_command_service: Optional[LiveCommandService] = None
        self.override_registry: Optional[OverrideRegistry] = None
        self.time_scheduler: Optional[Any] = None
        self.rule_engine: Optional[Any] = None
        self.db: Optional[Database] = None
        self.firmware_service: Optional[Any] = None
        self.system: Optional[Any] = None
        self.config_manager: Optional[Any] = None
        self.notification_service: Optional[Any] = None


system_container = SystemContainer()


def get_device_manager() -> DeviceManager:
    if system_container.device_manager is None:
        raise RuntimeError("DeviceManager is not initialized in API container")
    return system_container.device_manager


def get_node_manager() -> NodeManager:
    if system_container.node_manager is None:
        raise RuntimeError("NodeManager is not initialized in API container")
    return system_container.node_manager


def get_pin_manager() -> Optional[PinManager]:
    return system_container.pin_manager



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


def get_time_scheduler() -> Any:
    if system_container.time_scheduler is None:
        raise RuntimeError("TimeScheduler is not initialized in API container")
    return system_container.time_scheduler


def get_rule_engine() -> Any:
    if system_container.rule_engine is None:
        raise RuntimeError("RuleEngine is not initialized in API container")
    return system_container.rule_engine


def get_database() -> Database:
    if system_container.db is None:
        raise RuntimeError("Database is not initialized in API container")
    return system_container.db


def get_firmware_service():
    if system_container.firmware_service is None:
        from firmware.service import FirmwareService
        system_container.firmware_service = FirmwareService(database=system_container.db)
    return system_container.firmware_service


def get_system():
    return system_container.system


def get_config_manager():
    if system_container.config_manager is None:
        from config_manager.service import ConfigManagerService
        from core.settings import settings
        system_container.config_manager = ConfigManagerService(settings.config_path)
    return system_container.config_manager


def get_notification_service():
    from services.notifications import NotificationService
    if system_container.notification_service is None:
        cfg = {}
        if system_container.config_manager:
            try:
                cfg = system_container.config_manager.load_active_config(mask=False).get("notifications", {})
            except Exception:
                pass
        system_container.notification_service = NotificationService(cfg)
    else:
        # Keep notification service configuration updated from latest active config
        if system_container.config_manager:
            try:
                fresh_notif = system_container.config_manager.load_active_config(mask=False).get("notifications", {})
                if fresh_notif:
                    system_container.notification_service.update_config(fresh_notif)
            except Exception:
                pass
    return system_container.notification_service


