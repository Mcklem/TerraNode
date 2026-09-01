import asyncio
from typing import Dict, List, Optional
from devices.base_device import BaseDevice
from devices.sensor import Sensor
from devices.actuator import Actuator
from core.node_manager import NodeManager
from core.pin_manager import PinManager
from core.registry import DEVICE_REGISTRY, DeviceRegistry
from utils.logging import get_logger


class DeviceManager:
    """Manages creation, lifecycle, and access to all sensors and actuators."""

    def __init__(
        self,
        node_manager: NodeManager,
        pin_manager: PinManager,
        registry: DeviceRegistry = DEVICE_REGISTRY,
    ):
        self.node_manager = node_manager
        self.pin_manager = pin_manager
        self.registry = registry
        self._devices: Dict[str, BaseDevice] = {}
        self._logger = get_logger("DeviceManager")

    def initialize_devices(self, devices_cfg: Dict[str, dict]) -> None:
        """Instantiate devices from config dictionary after validating pins."""
        # First validate pin allocations
        self.pin_manager.validate_all(devices_cfg)

        for dev_id, dev_cfg in devices_cfg.items():
            dev_type = dev_cfg.get("type")
            node_id = dev_cfg.get("node")

            node = self.node_manager.get_node(node_id)
            if not node:
                raise ValueError(f"Device '{dev_id}' references unknown node '{node_id}'")

            driver_cls = self.registry.get(dev_type)
            device_instance = driver_cls(
                device_id=dev_id,
                device_type=dev_type,
                node=node,
                config=dev_cfg,
            )
            self._devices[dev_id] = device_instance
            self._logger.info(f"Initialized device '{dev_id}' (type={dev_type}, node={node_id})")

    def get_device(self, device_id: str) -> Optional[BaseDevice]:
        return self._devices.get(device_id)

    def get_all_devices(self) -> List[BaseDevice]:
        return list(self._devices.values())

    def get_sensors(self) -> List[Sensor]:
        return [d for d in self._devices.values() if isinstance(d, Sensor)]

    def get_actuators(self) -> List[Actuator]:
        return [d for d in self._devices.values() if isinstance(d, Actuator)]

    async def start_all(self) -> None:
        """Start hardware initialization on all devices."""
        for dev in self._devices.values():
            if dev.node.is_connected():
                try:
                    await dev.start()
                except Exception as e:
                    self._logger.error(f"Failed starting device '{dev.id}': {e}")

    async def stop_all(self) -> None:
        """Teardown all devices."""
        for dev in self._devices.values():
            try:
                await dev.stop()
            except Exception as e:
                self._logger.warning(f"Error stopping device '{dev.id}': {e}")
