from typing import Dict, Type
from devices.base_device import BaseDevice
from devices.sensors.ldr import LDRSensor
from devices.sensors.bmp180 import BMP180Sensor
from devices.sensors.soil_moisture import SoilMoistureSensor
from devices.actuators.relay import RelayActuator
from devices.actuators.servo import ServoActuator
from devices.actuators.led import LedActuator


class DeviceRegistry:
    """Registry mapping string device types to Python driver implementation classes."""

    def __init__(self):
        self._registry: Dict[str, Type[BaseDevice]] = {
            "ldr": LDRSensor,
            "bmp180": BMP180Sensor,
            "soil_moisture": SoilMoistureSensor,
            "relay": RelayActuator,
            "servo": ServoActuator,
            "led": LedActuator,
        }

    def register(self, type_name: str, cls: Type[BaseDevice]) -> None:
        """Register a new custom device driver class."""
        self._registry[type_name.lower()] = cls

    def get(self, type_name: str) -> Type[BaseDevice]:
        """Look up device driver class by type string."""
        type_key = type_name.lower()
        if type_key not in self._registry:
            raise KeyError(
                f"Unknown device type '{type_name}'. Registered types: {list(self._registry.keys())}"
            )
        return self._registry[type_key]

    def has(self, type_name: str) -> bool:
        return type_name.lower() in self._registry


# Global registry instance
DEVICE_REGISTRY = DeviceRegistry()
