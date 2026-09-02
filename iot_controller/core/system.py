import asyncio
from typing import Dict, Optional
from automation.rule_engine import RuleEngine
from core.config import ConfigLoader
from core.device_manager import DeviceManager
from core.event_bus import EventBus
from core.node_manager import NodeManager
from core.pin_manager import PinManager
from core.registry import DEVICE_REGISTRY
from core.scheduler import Scheduler
from core.settings import settings
from monitoring.health import HealthMonitor
from storage.database import Database
from storage.repositories import StorageManager
from utils.logging import get_logger, setup_logging


class ControllerSystem:
    """Unified system orchestrator implementing the 14-step deterministic startup sequence."""

    def __init__(
        self,
        config_path: Optional[str] = None,
        database_url: Optional[str] = None,
        use_mock: Optional[bool] = None,
    ):
        self.config_path = config_path or settings.config_path
        self.database_url = database_url or settings.database_url
        self.use_mock = use_mock if use_mock is not None else settings.mock_nodes
        self.config: Dict[str, dict] = {}

        self.logger = get_logger("ControllerSystem")
        self.node_manager = NodeManager()
        self.pin_manager = PinManager()
        self.device_manager = DeviceManager(self.node_manager, self.pin_manager, DEVICE_REGISTRY)
        self.event_bus = EventBus()
        self.scheduler = Scheduler(self.device_manager, self.event_bus)

        self.db: Optional[Database] = None
        self.storage_manager: Optional[StorageManager] = None
        self.override_registry: Optional[Any] = None
        self.command_dispatcher: Optional[Any] = None
        self.live_command_service: Optional[Any] = None
        self.rule_engine: Optional[RuleEngine] = None
        self.health_monitor: Optional[HealthMonitor] = None
        self.api_server: Optional[Any] = None
        self.api_task: Optional[asyncio.Task] = None
        self._running: bool = False

    async def start(self) -> None:
        """Execute the 14-step startup sequence."""
        # 3. Initialize logging with environment level
        setup_logging(settings.get_log_level_int())
        self.logger.info("Starting Distributed IoT Hardware Controller...")

        # 1. Load configuration & 2. Validate configuration
        loader = ConfigLoader(self.config_path)
        self.config = loader.load()

        # 4. Initialize database using environment/configured DATABASE_URL
        sys_cfg = self.config.get("system", {})
        db_url_override = sys_cfg.get("database") or self.database_url
        self.db = Database(database_url=db_url_override)
        await self.db.initialize()
        self.storage_manager = StorageManager(self.db, self.event_bus, node_manager=self.node_manager)
        self.storage_manager.start()

        # 5. Initialize Node Manager
        nodes_cfg = self.config.get("nodes", {})
        for node_id, node_cfg in nodes_cfg.items():
            if self.use_mock:
                node_cfg = dict(node_cfg)
                node_cfg["driver"] = "mock"
            self.node_manager.create_node(node_id, node_cfg)

        # 6. Connect Nodes
        self.logger.info("Connecting hardware nodes...")
        await self.node_manager.connect_all()
        for node in self.node_manager.get_all_nodes():
            if node.is_connected():
                await self.event_bus.publish(
                    "node.status_changed",
                    sender=node.id,
                    payload={"status": "CONNECTED"},
                )

        # 7. Validate pins/buses & 8. Initialize Device Manager & 9. Initialize devices
        devices_cfg = self.config.get("devices", {})
        self.device_manager.initialize_devices(devices_cfg)
        await self.device_manager.start_all()

        # 10. Start Event Bus (Implicitly ready)

        # 11. Start Scheduler
        log_readings = sys_cfg.get("log_readings", settings.log_readings)
        self.scheduler.log_readings = log_readings
        await self.scheduler.start()

        # 11b. Initialize Live Command & Override Service Layer
        from services.live_command import CommandDispatcher, LiveCommandService, OverrideRegistry
        self.override_registry = OverrideRegistry()
        self.command_dispatcher = CommandDispatcher(
            device_manager=self.device_manager,
            override_registry=self.override_registry,
            event_bus=self.event_bus,
        )
        self.live_command_service = LiveCommandService(
            device_manager=self.device_manager,
            node_manager=self.node_manager,
            override_registry=self.override_registry,
            dispatcher=self.command_dispatcher,
        )

        # 12. Start Rule Engine
        rules_cfg = self.config.get("rules", {})
        log_rule_evaluations = sys_cfg.get("log_rule_evaluations", settings.log_rule_evaluations)
        self.rule_engine = RuleEngine(
            rules_cfg,
            self.device_manager,
            self.event_bus,
            log_rule_evaluations=log_rule_evaluations,
            command_dispatcher=self.command_dispatcher,
        )
        self.rule_engine.start()

        # 13. Start Health Monitor
        self.health_monitor = HealthMonitor(self.node_manager, self.device_manager, self.event_bus)
        await self.health_monitor.start()

        # Populate API System Container
        from api.dependencies import system_container
        system_container.device_manager = self.device_manager
        system_container.node_manager = self.node_manager
        system_container.health_monitor = self.health_monitor
        system_container.live_command_service = self.live_command_service
        system_container.override_registry = self.override_registry
        system_container.db = self.db

        # 13b. Start FastAPI Web Service if enabled in settings
        if settings.enable_api:
            import uvicorn
            from api.app import create_app

            api_app = create_app()
            config = uvicorn.Config(
                app=api_app,
                host=settings.api_host,
                port=settings.api_port,
                log_level="info",
            )
            self.api_server = uvicorn.Server(config)
            self.api_task = asyncio.create_task(self.api_server.serve())
            self.logger.info(
                f"FastAPI Web Service started on http://{settings.api_host}:{settings.api_port}"
            )

        # 14. System READY
        self._running = True
        self.logger.info("=" * 60)
        self.logger.info(
            f"System '{sys_cfg.get('name', 'iot_controller')}' v{sys_cfg.get('version', '1.0')} is READY!"
        )
        self.logger.info("=" * 60)

    async def stop(self) -> None:
        """Graceful shutdown of all subsystems."""
        self.logger.info("Shutting down Distributed IoT Hardware Controller...")

        if self.api_server:
            self.api_server.should_exit = True
            if self.api_task and not self.api_task.done():
                try:
                    await asyncio.wait_for(self.api_task, timeout=3.0)
                except (asyncio.TimeoutError, asyncio.CancelledError, SystemExit, Exception):
                    pass

        if self.health_monitor:
            try:
                await self.health_monitor.stop()
            except Exception as e:
                self.logger.warning(f"Error stopping HealthMonitor: {e}")

        if self.rule_engine:
            try:
                self.rule_engine.stop()
            except Exception as e:
                self.logger.warning(f"Error stopping RuleEngine: {e}")

        if self.scheduler:
            try:
                await self.scheduler.stop()
            except Exception as e:
                self.logger.warning(f"Error stopping Scheduler: {e}")

        if self.device_manager:
            try:
                await self.device_manager.stop_all()
            except Exception as e:
                self.logger.warning(f"Error stopping devices: {e}")

        if self.node_manager:
            try:
                await self.node_manager.disconnect_all()
            except Exception as e:
                self.logger.warning(f"Error disconnecting nodes: {e}")

        if self.storage_manager:
            try:
                self.storage_manager.stop()
            except Exception as e:
                self.logger.warning(f"Error stopping StorageManager: {e}")

        self._running = False
        self.logger.info("System shutdown complete.")
