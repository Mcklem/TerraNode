import os
from typing import Any, Dict
import yaml


class ConfigurationError(Exception):
    """Exception raised when system configuration is invalid."""
    pass


class ConfigLoader:
    """Loads, normalizes, and validates system YAML configuration files."""

    def __init__(self, config_path: str):
        self.config_path = os.path.abspath(config_path)
        self.raw_config: Dict[str, Any] = {}

    def load(self) -> Dict[str, Any]:
        """Load YAML configuration file from disk and normalize nested structures."""
        if not os.path.exists(self.config_path):
            raise ConfigurationError(f"Configuration file not found at: {self.config_path}")

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.raw_config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigurationError(f"YAML syntax error in '{self.config_path}': {e}")

        self.normalize()
        self.validate()
        return self.raw_config

    def normalize(self) -> None:
        """Normalize configuration by extracting devices nested under nodes into global devices registry."""
        if not isinstance(self.raw_config, dict):
            return

        nodes = self.raw_config.get("nodes", {})
        if not isinstance(nodes, dict):
            return

        global_devices = self.raw_config.get("devices", {})
        if not isinstance(global_devices, dict):
            global_devices = {}

        for node_id, node_cfg in nodes.items():
            if not isinstance(node_cfg, dict):
                continue

            node_devices = node_cfg.get("devices")
            if isinstance(node_devices, dict):
                for dev_id, dev_cfg in node_devices.items():
                    if not isinstance(dev_cfg, dict):
                        raise ConfigurationError(
                            f"Device '{dev_id}' under node '{node_id}' must be a dictionary."
                        )

                    if dev_id in global_devices:
                        raise ConfigurationError(
                            f"Duplicate device ID '{dev_id}' found in configuration."
                        )

                    dev_cfg_copy = dict(dev_cfg)
                    dev_cfg_copy.setdefault("node", node_id)
                    global_devices[dev_id] = dev_cfg_copy

        self.raw_config["devices"] = global_devices

    def validate(self) -> None:
        """Validate structure and cross-references in configuration."""
        if not isinstance(self.raw_config, dict):
            raise ConfigurationError("Configuration file root must be a YAML dictionary.")

        # Ensure top-level sections exist
        nodes = self.raw_config.get("nodes", {})
        devices = self.raw_config.get("devices", {})

        if not isinstance(nodes, dict):
            raise ConfigurationError("'nodes' section must be a dictionary.")
        if not isinstance(devices, dict):
            raise ConfigurationError("'devices' section must be a dictionary.")

        # Validate nodes
        for node_id, node_cfg in nodes.items():
            if not isinstance(node_cfg, dict):
                raise ConfigurationError(f"Node '{node_id}' configuration must be a dictionary.")
            if "host" not in node_cfg and node_cfg.get("driver") != "mock":
                raise ConfigurationError(f"Node '{node_id}' missing required field 'host'.")

        # Validate devices and their node references
        for dev_id, dev_cfg in devices.items():
            if not isinstance(dev_cfg, dict):
                raise ConfigurationError(f"Device '{dev_id}' configuration must be a dictionary.")

            dev_type = dev_cfg.get("type")
            node_ref = dev_cfg.get("node")

            if not dev_type:
                raise ConfigurationError(f"Device '{dev_id}' missing required field 'type'.")
            if not node_ref:
                raise ConfigurationError(f"Device '{dev_id}' missing required field 'node'.")
            if node_ref not in nodes:
                raise ConfigurationError(
                    f"Device '{dev_id}' references non-existent node '{node_ref}'."
                )

        # Validate rules section if present
        rules = self.raw_config.get("rules", {})
        if not isinstance(rules, dict):
            raise ConfigurationError("'rules' section must be a dictionary.")

        for rule_id, rule_cfg in rules.items():
            if not isinstance(rule_cfg, dict):
                raise ConfigurationError(f"Rule '{rule_id}' configuration must be a dictionary.")
            cond = rule_cfg.get("condition", {})
            if cond:
                target_dev = cond.get("device")
                if target_dev and target_dev not in devices:
                    raise ConfigurationError(
                        f"Rule '{rule_id}' condition references non-existent device '{target_dev}'."
                    )
            actions = rule_cfg.get("actions", [])
            for action in actions:
                action_dev = action.get("device")
                if action_dev and action_dev not in devices:
                    raise ConfigurationError(
                        f"Rule '{rule_id}' action references non-existent device '{action_dev}'."
                    )
