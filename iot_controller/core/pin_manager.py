from typing import Any, Dict, List, Set, Tuple
from nodes.base_node import parse_pin
from utils.logging import get_logger


class PinConflictError(Exception):
    """Exception raised when a pin or bus conflict is detected."""
    pass


class PinManager:
    """Manages physical hardware resources, pin allocations, and bus address reservations."""

    def __init__(self):
        # Maps node_id -> set of allocated numeric pins
        self._allocated_pins: Dict[str, Dict[int, str]] = {}
        # Maps node_id -> set of allocated I2C addresses (address_int -> device_id)
        self._allocated_i2c: Dict[str, Dict[int, str]] = {}
        self._logger = get_logger("PinManager")

    def reset(self) -> None:
        self._allocated_pins.clear()
        self._allocated_i2c.clear()

    def register_device_pins(self, device_id: str, node_id: str, dev_config: Dict[str, Any]) -> None:
        """Register pin or I2C resources used by a device and check for conflicts."""
        if node_id not in self._allocated_pins:
            self._allocated_pins[node_id] = {}
        if node_id not in self._allocated_i2c:
            self._allocated_i2c[node_id] = {}

        bus = dev_config.get("bus")

        # Check I2C bus device
        if bus == "i2c" or "address" in dev_config:
            addr = dev_config.get("address")
            if isinstance(addr, str):
                addr = int(addr, 16) if addr.startswith("0x") else int(addr)

            if addr is not None:
                existing_dev = self._allocated_i2c[node_id].get(addr)
                if existing_dev and existing_dev != device_id:
                    raise PinConflictError(
                        f"\nPin/Bus Conflict Error:\n"
                        f"Node: {node_id}\n"
                        f"I2C Address: 0x{addr:02X}\n"
                        f"Devices in conflict: '{existing_dev}' and '{device_id}'"
                    )
                self._allocated_i2c[node_id][addr] = device_id
                self._logger.debug(f"Reserved I2C address 0x{addr:02X} on node '{node_id}' for device '{device_id}'")

        # Check GPIO / Analog pin device
        if "pin" in dev_config:
            raw_pin = dev_config["pin"]
            try:
                pin_num = parse_pin(raw_pin)
            except ValueError as e:
                raise PinConflictError(f"Device '{device_id}' on node '{node_id}': {e}")

            existing_dev = self._allocated_pins[node_id].get(pin_num)
            if existing_dev and existing_dev != device_id:
                raise PinConflictError(
                    f"\nPin Conflict Error:\n"
                    f"Node: {node_id}\n"
                    f"Pin: {raw_pin} (GPIO {pin_num})\n"
                    f"Devices in conflict: '{existing_dev}' and '{device_id}'"
                )
            self._allocated_pins[node_id][pin_num] = device_id
            self._logger.debug(
                f"Reserved pin {raw_pin} (GPIO {pin_num}) on node '{node_id}' for device '{device_id}'"
            )

    def validate_all(self, devices_config: Dict[str, Any]) -> None:
        """Validate all devices in configuration for pin and bus conflicts."""
        self.reset()
        for dev_id, dev_cfg in devices_config.items():
            node_id = dev_cfg.get("node")
            if node_id:
                self.register_device_pins(dev_id, node_id, dev_cfg)
        self._logger.info("Pin & I2C allocation validation passed without conflicts.")
