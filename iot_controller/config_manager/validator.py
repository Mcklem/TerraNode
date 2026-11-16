import re
from typing import Any, Dict, List, Optional, Set, Tuple
from config_manager.models import ValidationIssue, ValidationLevel, ValidationResult
from config_manager.yaml_parser import normalize_devices, parse_yaml, to_plain_dict
from core.registry import DEVICE_REGISTRY
from nodes.base_node import NODEMCU_PIN_MAP, NodeDriver, parse_pin


# Supported commands per actuator type
ACTUATOR_COMMANDS = {
    "relay": {"turn_on", "turn_off"},
    "led": {"turn_on", "turn_off"},
    "servo": {"set_position", "turn_on", "turn_off"},
}

# Supported evaluatable properties per sensor type
SENSOR_PROPERTIES = {
    "ldr": {"value", "raw_value"},
    "bmp180": {"temperature", "pressure", "altitude", "value"},
    "soil_moisture": {"value"},
}

# Relational comparison operators supported by RuleEngine / conditions.py
VALID_OPERATORS = {"<", ">", "<=", ">=", "==", "!="}

# Valid node drivers
VALID_DRIVERS = {d.value for d in NodeDriver}


def validate_cron_field(field_str: str, min_val: int, max_val: int) -> Optional[str]:
    """Validate a single cron field pattern."""
    if field_str == "*":
        return None
    for part in field_str.split(","):
        part = part.strip()
        if not part:
            return "Empty element in comma-separated cron field"
        if part.startswith("*/"):
            step_str = part[2:]
            if not step_str.isdigit() or int(step_str) <= 0:
                return f"Invalid cron step value '{step_str}'"
        elif "-" in part:
            bounds = part.split("-")
            if len(bounds) != 2 or not bounds[0].isdigit() or not bounds[1].isdigit():
                return f"Invalid cron range syntax '{part}'"
            low, high = int(bounds[0]), int(bounds[1])
            if low < min_val or high > max_val or low > high:
                return f"Cron range '{part}' out of bounds ({min_val}-{max_val})"
        else:
            if not part.isdigit():
                return f"Invalid cron component '{part}'"
            val = int(part)
            if val < min_val or val > max_val:
                return f"Cron value {val} out of bounds ({min_val}-{max_val})"
    return None


def validate_cron_string(cron_str: str) -> Optional[str]:
    """Validate a standard 5-field cron string."""
    parts = cron_str.strip().split()
    if len(parts) != 5:
        return f"Cron expression must have exactly 5 fields, got {len(parts)}: '{cron_str}'"
    specs = [
        ("minute", 0, 59),
        ("hour", 0, 23),
        ("day of month", 1, 31),
        ("month", 1, 12),
        ("day of week", 0, 7),
    ]
    for (name, min_v, max_v), field_val in zip(specs, parts):
        err = validate_cron_field(field_val, min_v, max_v)
        if err:
            return f"Error in {name} field '{field_val}': {err}"
    return None


class ConfigValidator:
    """Multi-level validator for TerraNode system configuration."""

    @classmethod
    def validate_yaml_string(cls, yaml_content: str) -> ValidationResult:
        """Validate raw YAML string across Level 1, Level 2, and Level 3."""
        errors: List[ValidationIssue] = []
        warnings: List[ValidationIssue] = []
        infos: List[ValidationIssue] = []

        # Level 1: Syntax Validation
        parsed_data, syntax_err, err_line = parse_yaml(yaml_content)
        if syntax_err:
            errors.append(
                ValidationIssue(
                    field="yaml_syntax",
                    message=f"YAML Syntax Error: {syntax_err}",
                    level=ValidationLevel.ERROR.value,
                    line=err_line,
                )
            )
            return ValidationResult(valid=False, errors=errors, warnings=warnings, infos=infos)

        if not parsed_data or not isinstance(parsed_data, dict):
            errors.append(
                ValidationIssue(
                    field="root",
                    message="Configuration root must be a YAML dictionary.",
                    level=ValidationLevel.ERROR.value,
                )
            )
            return ValidationResult(valid=False, errors=errors, warnings=warnings, infos=infos)

        # Level 2 & 3: Structural & Semantic Validation
        return cls.validate_dict(to_plain_dict(parsed_data))

    @classmethod
    def validate_dict(cls, raw_config: Dict[str, Any]) -> ValidationResult:
        """Validate configuration dictionary across Level 2 (structure) and Level 3 (semantics)."""
        errors: List[ValidationIssue] = []
        warnings: List[ValidationIssue] = []
        infos: List[ValidationIssue] = []

        if not isinstance(raw_config, dict):
            errors.append(
                ValidationIssue(
                    field="root",
                    message="Configuration root must be a dictionary.",
                    level=ValidationLevel.ERROR.value,
                )
            )
            return ValidationResult(valid=False, errors=errors, warnings=warnings, infos=infos)

        # Normalize devices into global structure for validation
        normalized = normalize_devices(raw_config)
        system_cfg = normalized.get("system")
        nodes_cfg = normalized.get("nodes")
        devices_cfg = normalized.get("devices")
        rules_cfg = normalized.get("rules")
        schedules_cfg = normalized.get("schedules")
        notifications_cfg = normalized.get("notifications")

        # ----------------------------------------------------------------------
        # 1. System Section Validation
        # ----------------------------------------------------------------------
        if system_cfg is None:
            warnings.append(
                ValidationIssue(
                    field="system",
                    message="Missing 'system' configuration section. Defaults will be applied.",
                    level=ValidationLevel.WARNING.value,
                )
            )
        elif not isinstance(system_cfg, dict):
            errors.append(
                ValidationIssue(
                    field="system",
                    message="'system' section must be a dictionary.",
                    level=ValidationLevel.ERROR.value,
                )
            )
        else:
            if not system_cfg.get("name"):
                warnings.append(
                    ValidationIssue(
                        field="system.name",
                        message="'system.name' is empty; default identifier will be used.",
                        level=ValidationLevel.WARNING.value,
                    )
                )
            if not system_cfg.get("database"):
                infos.append(
                    ValidationIssue(
                        field="system.database",
                        message="'system.database' not specified; default 'controller.db' will be used.",
                        level=ValidationLevel.INFO.value,
                    )
                )

        # ----------------------------------------------------------------------
        # 2. Nodes Section Validation
        # ----------------------------------------------------------------------
        if nodes_cfg is None:
            errors.append(
                ValidationIssue(
                    field="nodes",
                    message="Required 'nodes' section is missing.",
                    level=ValidationLevel.ERROR.value,
                )
            )
            nodes_cfg = {}
        elif not isinstance(nodes_cfg, dict):
            errors.append(
                ValidationIssue(
                    field="nodes",
                    message="'nodes' section must be a dictionary.",
                    level=ValidationLevel.ERROR.value,
                )
            )
            nodes_cfg = {}

        if not nodes_cfg:
            warnings.append(
                ValidationIssue(
                    field="nodes",
                    message="No hardware nodes are configured. Controller will run idle.",
                    level=ValidationLevel.WARNING.value,
                )
            )

        known_node_ids: Set[str] = set()
        for node_id, node_data in nodes_cfg.items():
            field_prefix = f"nodes.{node_id}"
            if not isinstance(node_data, dict):
                errors.append(
                    ValidationIssue(
                        field=field_prefix,
                        message=f"Node '{node_id}' configuration must be a dictionary.",
                        level=ValidationLevel.ERROR.value,
                    )
                )
                continue

            known_node_ids.add(node_id)
            driver = node_data.get("driver")
            host = node_data.get("host")
            port = node_data.get("port", 3030)
            enabled = node_data.get("enabled", True)

            # Check driver
            if not driver:
                errors.append(
                    ValidationIssue(
                        field=f"{field_prefix}.driver",
                        message=f"Node '{node_id}' is missing required field 'driver'.",
                        level=ValidationLevel.ERROR.value,
                    )
                )
            elif driver not in VALID_DRIVERS:
                errors.append(
                    ValidationIssue(
                        field=f"{field_prefix}.driver",
                        message=f"Node '{node_id}' specifies unknown driver '{driver}'. Supported: {sorted(list(VALID_DRIVERS))}.",
                        level=ValidationLevel.ERROR.value,
                    )
                )

            # Check host (required for non-mock drivers)
            if driver != "mock":
                if not host:
                    errors.append(
                        ValidationIssue(
                            field=f"{field_prefix}.host",
                            message=f"Node '{node_id}' missing required IP address or hostname 'host'.",
                            level=ValidationLevel.ERROR.value,
                        )
                    )
                elif isinstance(host, str):
                    host_clean = host.strip()
                    # Basic sanity check for valid hostname/IP
                    if not re.match(r"^[\w\.\-]+$", host_clean):
                        errors.append(
                            ValidationIssue(
                                field=f"{field_prefix}.host",
                                message=f"Node '{node_id}' has invalid host format: '{host}'.",
                                level=ValidationLevel.ERROR.value,
                            )
                        )

            # Check port
            raw_port = str(port)
            if "${" in raw_port:
                from core.config import interpolate_env_vars
                raw_port = interpolate_env_vars(raw_port)
            if raw_port:
                try:
                    port_int = int(raw_port)
                    if not (1 <= port_int <= 65535):
                        errors.append(
                            ValidationIssue(
                                field=f"{field_prefix}.port",
                                message=f"Node '{node_id}' port {port_int} out of range (1..65535).",
                                level=ValidationLevel.ERROR.value,
                            )
                        )
                except (ValueError, TypeError):
                    errors.append(
                        ValidationIssue(
                            field=f"{field_prefix}.port",
                            message=f"Node '{node_id}' port must be an integer.",
                            level=ValidationLevel.ERROR.value,
                        )
                    )

            # Check secure drivers auth_key
            if driver in ("secure_standard_firmata_wifi", "secure_firmata"):
                auth_key = node_data.get("auth_key")
                if not auth_key:
                    warnings.append(
                        ValidationIssue(
                            field=f"{field_prefix}.auth_key",
                            message=f"Node '{node_id}' uses secure driver '{driver}' but 'auth_key' is empty.",
                            level=ValidationLevel.WARNING.value,
                        )
                    )

            if not enabled:
                infos.append(
                    ValidationIssue(
                        field=f"{field_prefix}.enabled",
                        message=f"Node '{node_id}' is disabled. Its connected devices will not be reachable.",
                        level=ValidationLevel.INFO.value,
                    )
                )

        # ----------------------------------------------------------------------
        # 3. Devices Section & Pin Conflict Validation
        # ----------------------------------------------------------------------
        if devices_cfg is None:
            devices_cfg = {}
        elif not isinstance(devices_cfg, dict):
            errors.append(
                ValidationIssue(
                    field="devices",
                    message="'devices' section must be a dictionary.",
                    level=ValidationLevel.ERROR.value,
                )
            )
            devices_cfg = {}

        # Pin & I2C allocation maps per node: node_id -> pin_num -> dev_id
        allocated_pins: Dict[str, Dict[int, str]] = {}
        allocated_i2c: Dict[str, Dict[int, str]] = {}

        known_sensor_ids: Set[str] = set()
        known_actuator_ids: Set[str] = set()
        device_types_by_id: Dict[str, str] = {}

        for dev_id, dev_data in devices_cfg.items():
            field_prefix = f"devices.{dev_id}"
            if not isinstance(dev_data, dict):
                errors.append(
                    ValidationIssue(
                        field=field_prefix,
                        message=f"Device '{dev_id}' configuration must be a dictionary.",
                        level=ValidationLevel.ERROR.value,
                    )
                )
                continue

            dev_type = dev_data.get("type")
            node_ref = dev_data.get("node")

            if not dev_type:
                errors.append(
                    ValidationIssue(
                        field=f"{field_prefix}.type",
                        message=f"Device '{dev_id}' missing required field 'type'.",
                        level=ValidationLevel.ERROR.value,
                    )
                )
                continue

            dev_type_str = str(dev_type).lower()
            device_types_by_id[dev_id] = dev_type_str

            if not DEVICE_REGISTRY.has(dev_type_str):
                errors.append(
                    ValidationIssue(
                        field=f"{field_prefix}.type",
                        message=f"Device '{dev_id}' specifies unknown type '{dev_type}'. Registered: {list(DEVICE_REGISTRY._registry.keys())}.",
                        level=ValidationLevel.ERROR.value,
                    )
                )
                continue

            # Classify device as sensor or actuator
            if dev_type_str in ("ldr", "bmp180", "soil_moisture"):
                known_sensor_ids.add(dev_id)
            elif dev_type_str in ("relay", "servo", "led"):
                known_actuator_ids.add(dev_id)

            if not node_ref:
                errors.append(
                    ValidationIssue(
                        field=f"{field_prefix}.node",
                        message=f"Device '{dev_id}' missing parent 'node' reference.",
                        level=ValidationLevel.ERROR.value,
                    )
                )
                continue
            elif node_ref not in known_node_ids:
                errors.append(
                    ValidationIssue(
                        field=f"{field_prefix}.node",
                        message=f"Device '{dev_id}' references non-existent node '{node_ref}'.",
                        level=ValidationLevel.ERROR.value,
                    )
                )
                continue

            # Pin & Bus validation
            bus = dev_data.get("bus")
            if bus == "i2c" or dev_type_str == "bmp180":
                # Validate I2C address
                addr_val = dev_data.get("address", 0x77)
                try:
                    if isinstance(addr_val, str):
                        addr_int = int(addr_val, 16) if addr_val.startswith("0x") else int(addr_val)
                    else:
                        addr_int = int(addr_val)
                    if not (0x08 <= addr_int <= 0x77):
                        warnings.append(
                            ValidationIssue(
                                field=f"{field_prefix}.address",
                                message=f"Device '{dev_id}' I2C address 0x{addr_int:02X} is outside standard range (0x08..0x77).",
                                level=ValidationLevel.WARNING.value,
                            )
                        )
                    # I2C conflict check
                    node_i2c = allocated_i2c.setdefault(node_ref, {})
                    if addr_int in node_i2c and node_i2c[addr_int] != dev_id:
                        errors.append(
                            ValidationIssue(
                                field=f"{field_prefix}.address",
                                message=f"I2C conflict on node '{node_ref}': address 0x{addr_int:02X} already claimed by device '{node_i2c[addr_int]}'.",
                                level=ValidationLevel.ERROR.value,
                            )
                        )
                    else:
                        node_i2c[addr_int] = dev_id
                except (ValueError, TypeError):
                    errors.append(
                        ValidationIssue(
                            field=f"{field_prefix}.address",
                            message=f"Device '{dev_id}' has invalid I2C address '{addr_val}'.",
                            level=ValidationLevel.ERROR.value,
                        )
                    )
            elif "pin" in dev_data:
                raw_pin = dev_data["pin"]
                try:
                    pin_num = parse_pin(raw_pin)
                    raw_pin_str = str(raw_pin).strip().upper()

                    # Analog vs Digital check
                    if dev_type_str in ("ldr", "soil_moisture"):
                        if raw_pin_str not in ("A0", "0"):
                            warnings.append(
                                ValidationIssue(
                                    field=f"{field_prefix}.pin",
                                    message=f"Analog sensor '{dev_id}' configured on pin '{raw_pin}'. ESP8266 typically only supports 'A0' for ADC.",
                                    level=ValidationLevel.WARNING.value,
                                )
                            )
                    elif dev_type_str in ("relay", "servo", "led"):
                        if raw_pin_str == "A0":
                            errors.append(
                                ValidationIssue(
                                    field=f"{field_prefix}.pin",
                                    message=f"Actuator '{dev_id}' ({dev_type_str}) cannot be assigned to analog input pin 'A0'.",
                                    level=ValidationLevel.ERROR.value,
                                )
                            )

                    # GPIO Conflict check
                    node_pins = allocated_pins.setdefault(node_ref, {})
                    if pin_num in node_pins and node_pins[pin_num] != dev_id:
                        errors.append(
                            ValidationIssue(
                                field=f"{field_prefix}.pin",
                                message=f"Pin conflict on node '{node_ref}': Pin '{raw_pin}' (GPIO {pin_num}) already claimed by device '{node_pins[pin_num]}'.",
                                level=ValidationLevel.ERROR.value,
                            )
                        )
                    else:
                        node_pins[pin_num] = dev_id
                except ValueError as e:
                    errors.append(
                        ValidationIssue(
                            field=f"{field_prefix}.pin",
                            message=f"Device '{dev_id}' pin error: {e}",
                            level=ValidationLevel.ERROR.value,
                        )
                    )

            # Polling interval validation for sensors
            if dev_type_str in ("ldr", "bmp180", "soil_moisture"):
                poll_interval = dev_data.get("poll_interval")
                if poll_interval is not None:
                    try:
                        p_val = float(poll_interval)
                        if p_val <= 0:
                            errors.append(
                                ValidationIssue(
                                    field=f"{field_prefix}.poll_interval",
                                    message=f"Sensor '{dev_id}' poll_interval must be greater than 0, got {p_val}.",
                                    level=ValidationLevel.ERROR.value,
                                )
                            )
                        elif p_val < 2.0:
                            warnings.append(
                                ValidationIssue(
                                    field=f"{field_prefix}.poll_interval",
                                    message=f"Sensor '{dev_id}' poll_interval ({p_val}s) is very frequent; may cause high WiFi/network load.",
                                    level=ValidationLevel.WARNING.value,
                                )
                            )
                    except (ValueError, TypeError):
                        errors.append(
                            ValidationIssue(
                                field=f"{field_prefix}.poll_interval",
                                message=f"Sensor '{dev_id}' poll_interval must be numeric.",
                                level=ValidationLevel.ERROR.value,
                            )
                        )

            # Type-specific parameters
            if dev_type_str == "servo":
                min_angle = dev_data.get("min_angle", 0)
                max_angle = dev_data.get("max_angle", 180)
                try:
                    min_a = int(min_angle)
                    max_a = int(max_angle)
                    if not (0 <= min_a <= 180 and 0 <= max_a <= 180):
                        errors.append(
                            ValidationIssue(
                                field=f"{field_prefix}.min_angle",
                                message=f"Servo angles must be between 0 and 180 degrees (got {min_a}..{max_a}).",
                                level=ValidationLevel.ERROR.value,
                            )
                        )
                    elif min_a >= max_a:
                        errors.append(
                            ValidationIssue(
                                field=f"{field_prefix}.min_angle",
                                message=f"Servo min_angle ({min_a}) must be strictly less than max_angle ({max_a}).",
                                level=ValidationLevel.ERROR.value,
                            )
                        )
                except (ValueError, TypeError):
                    errors.append(
                        ValidationIssue(
                            field=f"{field_prefix}.min_angle",
                            message="Servo min_angle and max_angle must be integers.",
                            level=ValidationLevel.ERROR.value,
                        )
                    )
            elif dev_type_str == "soil_moisture":
                calib = dev_data.get("calibration")
                if isinstance(calib, dict):
                    dry = calib.get("dry")
                    wet = calib.get("wet")
                    if dry is not None and wet is not None:
                        try:
                            if float(dry) == float(wet):
                                warnings.append(
                                    ValidationIssue(
                                        field=f"{field_prefix}.calibration",
                                        message=f"Soil moisture '{dev_id}' calibration dry and wet values are identical ({dry}).",
                                        level=ValidationLevel.WARNING.value,
                                    )
                                )
                        except (ValueError, TypeError):
                            pass

        # ----------------------------------------------------------------------
        # 4. Rules Section Validation
        # ----------------------------------------------------------------------
        if rules_cfg is not None:
            if not isinstance(rules_cfg, dict):
                errors.append(
                    ValidationIssue(
                        field="rules",
                        message="'rules' section must be a dictionary.",
                        level=ValidationLevel.ERROR.value,
                    )
                )
            else:
                for rule_id, rule_data in rules_cfg.items():
                    field_prefix = f"rules.{rule_id}"
                    if not isinstance(rule_data, dict):
                        errors.append(
                            ValidationIssue(
                                field=field_prefix,
                                message=f"Rule '{rule_id}' configuration must be a dictionary.",
                                level=ValidationLevel.ERROR.value,
                            )
                        )
                        continue

                    # Condition validation
                    cond = rule_data.get("condition")
                    if not cond or not isinstance(cond, dict):
                        errors.append(
                            ValidationIssue(
                                field=f"{field_prefix}.condition",
                                message=f"Rule '{rule_id}' missing required 'condition' dictionary.",
                                level=ValidationLevel.ERROR.value,
                            )
                        )
                    else:
                        target_dev = cond.get("device")
                        prop = cond.get("property", "value")
                        op = cond.get("operator")
                        val = cond.get("value")

                        if not target_dev:
                            errors.append(
                                ValidationIssue(
                                    field=f"{field_prefix}.condition.device",
                                    message=f"Rule '{rule_id}' condition missing 'device'.",
                                    level=ValidationLevel.ERROR.value,
                                )
                            )
                        elif target_dev not in devices_cfg:
                            errors.append(
                                ValidationIssue(
                                    field=f"{field_prefix}.condition.device",
                                    message=f"Rule '{rule_id}' condition references non-existent device '{target_dev}'.",
                                    level=ValidationLevel.ERROR.value,
                                )
                            )
                        elif target_dev not in known_sensor_ids:
                            warnings.append(
                                ValidationIssue(
                                    field=f"{field_prefix}.condition.device",
                                    message=f"Rule '{rule_id}' condition targets '{target_dev}' which is an actuator, not a sensor.",
                                    level=ValidationLevel.WARNING.value,
                                )
                            )
                        else:
                            # Verify property is supported by this sensor type
                            sensor_type = device_types_by_id.get(target_dev, "")
                            valid_props = SENSOR_PROPERTIES.get(sensor_type, {"value"})
                            if prop not in valid_props:
                                warnings.append(
                                    ValidationIssue(
                                        field=f"{field_prefix}.condition.property",
                                        message=f"Sensor '{target_dev}' ({sensor_type}) property '{prop}' may not exist. Expected: {valid_props}.",
                                        level=ValidationLevel.WARNING.value,
                                    )
                                )

                        if not op:
                            errors.append(
                                ValidationIssue(
                                    field=f"{field_prefix}.condition.operator",
                                    message=f"Rule '{rule_id}' condition missing 'operator'.",
                                    level=ValidationLevel.ERROR.value,
                                )
                            )
                        elif op not in VALID_OPERATORS:
                            errors.append(
                                ValidationIssue(
                                    field=f"{field_prefix}.condition.operator",
                                    message=f"Rule '{rule_id}' operator '{op}' is unsupported. Valid: {list(VALID_OPERATORS)}.",
                                    level=ValidationLevel.ERROR.value,
                                )
                            )

                        if val is None:
                            errors.append(
                                ValidationIssue(
                                    field=f"{field_prefix}.condition.value",
                                    message=f"Rule '{rule_id}' condition missing threshold 'value'.",
                                    level=ValidationLevel.ERROR.value,
                                )
                            )

                    # Cooldown validation
                    cooldown = rule_data.get("cooldown")
                    if cooldown is not None:
                        try:
                            c_val = float(cooldown)
                            if c_val < 0:
                                errors.append(
                                    ValidationIssue(
                                        field=f"{field_prefix}.cooldown",
                                        message=f"Rule '{rule_id}' cooldown cannot be negative.",
                                        level=ValidationLevel.ERROR.value,
                                    )
                                )
                        except (ValueError, TypeError):
                            errors.append(
                                ValidationIssue(
                                    field=f"{field_prefix}.cooldown",
                                    message=f"Rule '{rule_id}' cooldown must be a number.",
                                    level=ValidationLevel.ERROR.value,
                                )
                            )

                    # Actions validation
                    actions = rule_data.get("actions")
                    if not actions or not isinstance(actions, list):
                        errors.append(
                            ValidationIssue(
                                field=f"{field_prefix}.actions",
                                message=f"Rule '{rule_id}' must contain a non-empty list of 'actions'.",
                                level=ValidationLevel.ERROR.value,
                            )
                        )
                    else:
                        for idx, action in enumerate(actions):
                            act_prefix = f"{field_prefix}.actions[{idx}]"
                            if not isinstance(action, dict):
                                errors.append(
                                    ValidationIssue(
                                        field=act_prefix,
                                        message=f"Rule '{rule_id}' action must be a dictionary.",
                                        level=ValidationLevel.ERROR.value,
                                    )
                                )
                                continue

                            act_type = action.get("type")
                            is_notification = act_type == "notification" or "channel" in action

                            if is_notification:
                                notif_channel = action.get("channel", "all")
                                valid_channels = {"email", "telegram", "webhook", "all"}
                                if notif_channel not in valid_channels:
                                    errors.append(
                                        ValidationIssue(
                                            field=f"{act_prefix}.channel",
                                            message=f"Rule '{rule_id}' notification channel '{notif_channel}' invalid. Supported: {sorted(list(valid_channels))}.",
                                            level=ValidationLevel.ERROR.value,
                                        )
                                    )
                                notif_msg = action.get("message")
                                if not notif_msg or not str(notif_msg).strip():
                                    errors.append(
                                        ValidationIssue(
                                            field=f"{act_prefix}.message",
                                            message=f"Rule '{rule_id}' notification action missing required 'message'.",
                                            level=ValidationLevel.ERROR.value,
                                        )
                                    )
                                webhook_target = action.get("webhook_id")
                                if webhook_target and notif_channel in ("webhook", "all"):
                                    known_webhooks = (
                                        notifications_cfg.get("webhooks", {})
                                        if isinstance(notifications_cfg, dict)
                                        else {}
                                    )
                                    if isinstance(known_webhooks, dict) and webhook_target not in known_webhooks:
                                        warnings.append(
                                            ValidationIssue(
                                                field=f"{act_prefix}.webhook_id",
                                                message=f"Rule '{rule_id}' action references webhook '{webhook_target}' which is not defined in notifications.webhooks.",
                                                level=ValidationLevel.WARNING.value,
                                            )
                                        )
                                continue

                            # Actuator action validation
                            act_dev = action.get("device")
                            act_cmd = action.get("command")

                            if not act_dev:
                                errors.append(
                                    ValidationIssue(
                                        field=f"{act_prefix}.device",
                                        message=f"Rule '{rule_id}' action missing target 'device'.",
                                        level=ValidationLevel.ERROR.value,
                                    )
                                )
                            elif act_dev not in devices_cfg:
                                errors.append(
                                    ValidationIssue(
                                        field=f"{act_prefix}.device",
                                        message=f"Rule '{rule_id}' action references non-existent device '{act_dev}'.",
                                        level=ValidationLevel.ERROR.value,
                                    )
                                )
                            elif act_dev in known_sensor_ids:
                                errors.append(
                                    ValidationIssue(
                                        field=f"{act_prefix}.device",
                                        message=f"Rule '{rule_id}' action targets sensor '{act_dev}'. Actions can only target actuators.",
                                        level=ValidationLevel.ERROR.value,
                                    )
                                )
                            elif act_dev in known_actuator_ids:
                                act_type_str = device_types_by_id.get(act_dev, "")
                                valid_cmds = ACTUATOR_COMMANDS.get(act_type_str, set())
                                if act_cmd and act_cmd not in valid_cmds:
                                    errors.append(
                                        ValidationIssue(
                                            field=f"{act_prefix}.command",
                                            message=f"Actuator '{act_dev}' ({act_type_str}) does not support command '{act_cmd}'. Valid: {list(valid_cmds)}.",
                                            level=ValidationLevel.ERROR.value,
                                        )
                                    )

                            if not act_cmd:
                                errors.append(
                                    ValidationIssue(
                                        field=f"{act_prefix}.command",
                                        message=f"Rule '{rule_id}' action missing 'command'.",
                                        level=ValidationLevel.ERROR.value,
                                    )
                                )

        # ----------------------------------------------------------------------
        # 5. Schedules Section Validation
        # ----------------------------------------------------------------------
        if schedules_cfg is not None:
            if not isinstance(schedules_cfg, dict):
                errors.append(
                    ValidationIssue(
                        field="schedules",
                        message="'schedules' section must be a dictionary.",
                        level=ValidationLevel.ERROR.value,
                    )
                )
            else:
                for sched_id, sched_data in schedules_cfg.items():
                    field_prefix = f"schedules.{sched_id}"
                    if not isinstance(sched_data, dict):
                        errors.append(
                            ValidationIssue(
                                field=field_prefix,
                                message=f"Schedule '{sched_id}' configuration must be a dictionary.",
                                level=ValidationLevel.ERROR.value,
                            )
                        )
                        continue

                    target_dev = sched_data.get("device")
                    cmd = sched_data.get("command")
                    stop_cmd = sched_data.get("stop_command")

                    if not target_dev:
                        errors.append(
                            ValidationIssue(
                                field=f"{field_prefix}.device",
                                message=f"Schedule '{sched_id}' missing target 'device'.",
                                level=ValidationLevel.ERROR.value,
                            )
                        )
                    elif target_dev not in devices_cfg:
                        errors.append(
                            ValidationIssue(
                                field=f"{field_prefix}.device",
                                message=f"Schedule '{sched_id}' references non-existent device '{target_dev}'.",
                                level=ValidationLevel.ERROR.value,
                            )
                        )
                    elif target_dev in known_sensor_ids:
                        errors.append(
                            ValidationIssue(
                                field=f"{field_prefix}.device",
                                message=f"Schedule '{sched_id}' targets sensor '{target_dev}'. Schedules can only control actuators.",
                                level=ValidationLevel.ERROR.value,
                            )
                        )
                    elif target_dev in known_actuator_ids:
                        act_type = device_types_by_id.get(target_dev, "")
                        valid_cmds = ACTUATOR_COMMANDS.get(act_type, set())
                        if cmd and cmd not in valid_cmds:
                            errors.append(
                                ValidationIssue(
                                    field=f"{field_prefix}.command",
                                    message=f"Actuator '{target_dev}' ({act_type}) does not support command '{cmd}'. Valid: {list(valid_cmds)}.",
                                    level=ValidationLevel.ERROR.value,
                                )
                            )
                        if stop_cmd and stop_cmd not in valid_cmds:
                            errors.append(
                                ValidationIssue(
                                    field=f"{field_prefix}.stop_command",
                                    message=f"Actuator '{target_dev}' ({act_type}) does not support stop_command '{stop_cmd}'. Valid: {list(valid_cmds)}.",
                                    level=ValidationLevel.ERROR.value,
                                )
                            )

                    if not cmd:
                        errors.append(
                            ValidationIssue(
                                field=f"{field_prefix}.command",
                                message=f"Schedule '{sched_id}' missing required field 'command'.",
                                level=ValidationLevel.ERROR.value,
                            )
                        )

                    # Trigger checks: at least one trigger must be defined
                    has_trigger = False
                    if sched_data.get("interval") is not None:
                        has_trigger = True
                        try:
                            inv = float(sched_data["interval"])
                            if inv <= 0:
                                errors.append(
                                    ValidationIssue(
                                        field=f"{field_prefix}.interval",
                                        message=f"Schedule '{sched_id}' interval must be > 0.",
                                        level=ValidationLevel.ERROR.value,
                                    )
                                )
                        except (ValueError, TypeError):
                            errors.append(
                                ValidationIssue(
                                    field=f"{field_prefix}.interval",
                                    message=f"Schedule '{sched_id}' interval must be a number.",
                                    level=ValidationLevel.ERROR.value,
                                )
                            )

                    if sched_data.get("time"):
                        has_trigger = True
                        time_str = str(sched_data["time"]).strip()
                        if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", time_str):
                            errors.append(
                                ValidationIssue(
                                    field=f"{field_prefix}.time",
                                    message=f"Schedule '{sched_id}' daily time must be in 'HH:MM' 24-hour format, got '{time_str}'.",
                                    level=ValidationLevel.ERROR.value,
                                )
                            )

                    if sched_data.get("cron"):
                        has_trigger = True
                        cron_err = validate_cron_string(str(sched_data["cron"]))
                        if cron_err:
                            errors.append(
                                ValidationIssue(
                                    field=f"{field_prefix}.cron",
                                    message=f"Schedule '{sched_id}' cron error: {cron_err}",
                                    level=ValidationLevel.ERROR.value,
                                )
                            )

                    if not has_trigger:
                        errors.append(
                            ValidationIssue(
                                field=field_prefix,
                                message=f"Schedule '{sched_id}' must specify at least one trigger: 'time', 'interval', or 'cron'.",
                                level=ValidationLevel.ERROR.value,
                            )
                        )

                    # Duration check
                    if sched_data.get("duration") is not None:
                        try:
                            dur = float(sched_data["duration"])
                            if dur <= 0:
                                errors.append(
                                    ValidationIssue(
                                        field=f"{field_prefix}.duration",
                                        message=f"Schedule '{sched_id}' duration must be > 0.",
                                        level=ValidationLevel.ERROR.value,
                                    )
                                )
                        except (ValueError, TypeError):
                            errors.append(
                                ValidationIssue(
                                    field=f"{field_prefix}.duration",
                                    message=f"Schedule '{sched_id}' duration must be a number.",
                                    level=ValidationLevel.ERROR.value,
                                )
                            )

        # ----------------------------------------------------------------------
        # 6. Notifications Section Validation
        # ----------------------------------------------------------------------
        if notifications_cfg is not None:
            if not isinstance(notifications_cfg, dict):
                errors.append(
                    ValidationIssue(
                        field="notifications",
                        message="'notifications' section must be a dictionary.",
                        level=ValidationLevel.ERROR.value,
                    )
                )
            else:
                # 6.1 Email validation
                email_cfg = notifications_cfg.get("email")
                if email_cfg is not None:
                    if not isinstance(email_cfg, dict):
                        errors.append(
                            ValidationIssue(
                                field="notifications.email",
                                message="'notifications.email' must be a dictionary.",
                                level=ValidationLevel.ERROR.value,
                            )
                        )
                    else:
                        email_enabled = email_cfg.get("enabled", False)
                        smtp_host = email_cfg.get("smtp_host")
                        smtp_port = email_cfg.get("smtp_port")
                        to_addrs = email_cfg.get("to_addresses")

                        if smtp_port is not None:
                            raw_p = str(smtp_port)
                            if "${" in raw_p:
                                from core.config import interpolate_env_vars
                                raw_p = interpolate_env_vars(raw_p)
                            if raw_p:
                                try:
                                    p_int = int(raw_p)
                                    if not (1 <= p_int <= 65535):
                                        errors.append(
                                            ValidationIssue(
                                                field="notifications.email.smtp_port",
                                                message=f"SMTP port {p_int} out of valid range (1..65535).",
                                                level=ValidationLevel.ERROR.value,
                                            )
                                        )
                                except (ValueError, TypeError):
                                    errors.append(
                                        ValidationIssue(
                                            field="notifications.email.smtp_port",
                                            message="SMTP port must be an integer.",
                                            level=ValidationLevel.ERROR.value,
                                        )
                                    )

                        if email_enabled:
                            if not smtp_host:
                                errors.append(
                                    ValidationIssue(
                                        field="notifications.email.smtp_host",
                                        message="Email notifications enabled but 'smtp_host' is empty.",
                                        level=ValidationLevel.ERROR.value,
                                    )
                                )
                            if not to_addrs:
                                errors.append(
                                    ValidationIssue(
                                        field="notifications.email.to_addresses",
                                        message="Email notifications enabled but no recipient addresses in 'to_addresses'.",
                                        level=ValidationLevel.ERROR.value,
                                    )
                                )

                # 6.2 Telegram validation
                telegram_cfg = notifications_cfg.get("telegram")
                if telegram_cfg is not None:
                    if not isinstance(telegram_cfg, dict):
                        errors.append(
                            ValidationIssue(
                                field="notifications.telegram",
                                message="'notifications.telegram' must be a dictionary.",
                                level=ValidationLevel.ERROR.value,
                            )
                        )
                    else:
                        tel_enabled = telegram_cfg.get("enabled", False)
                        bot_token = telegram_cfg.get("bot_token")
                        chat_id = telegram_cfg.get("chat_id")

                        if tel_enabled:
                            if not bot_token:
                                errors.append(
                                    ValidationIssue(
                                        field="notifications.telegram.bot_token",
                                        message="Telegram notifications enabled but 'bot_token' is empty.",
                                        level=ValidationLevel.ERROR.value,
                                    )
                                )
                            if not chat_id:
                                errors.append(
                                    ValidationIssue(
                                        field="notifications.telegram.chat_id",
                                        message="Telegram notifications enabled but 'chat_id' is empty.",
                                        level=ValidationLevel.ERROR.value,
                                    )
                                )

                # 6.3 Webhooks validation
                webhooks_cfg = notifications_cfg.get("webhooks")
                if webhooks_cfg is not None:
                    if not isinstance(webhooks_cfg, dict):
                        errors.append(
                            ValidationIssue(
                                field="notifications.webhooks",
                                message="'notifications.webhooks' must be a dictionary of webhook configurations.",
                                level=ValidationLevel.ERROR.value,
                            )
                        )
                    else:
                        for w_id, w_data in webhooks_cfg.items():
                            w_prefix = f"notifications.webhooks.{w_id}"
                            if not isinstance(w_data, dict):
                                errors.append(
                                    ValidationIssue(
                                        field=w_prefix,
                                        message=f"Webhook '{w_id}' configuration must be a dictionary.",
                                        level=ValidationLevel.ERROR.value,
                                    )
                                )
                                continue

                            w_url = w_data.get("url")
                            w_method = w_data.get("method", "POST")
                            w_headers = w_data.get("headers")

                            if not w_url:
                                errors.append(
                                    ValidationIssue(
                                        field=f"{w_prefix}.url",
                                        message=f"Webhook '{w_id}' missing required field 'url'.",
                                        level=ValidationLevel.ERROR.value,
                                    )
                                )
                            elif not (str(w_url).startswith("http://") or str(w_url).startswith("https://")):
                                errors.append(
                                    ValidationIssue(
                                        field=f"{w_prefix}.url",
                                        message=f"Webhook '{w_id}' URL must start with http:// or https:// (got '{w_url}').",
                                        level=ValidationLevel.ERROR.value,
                                    )
                                )

                            if w_method and str(w_method).upper() not in ("GET", "POST", "PUT"):
                                errors.append(
                                    ValidationIssue(
                                        field=f"{w_prefix}.method",
                                        message=f"Webhook '{w_id}' method '{w_method}' unsupported. Expected GET, POST, or PUT.",
                                        level=ValidationLevel.ERROR.value,
                                    )
                                )

                            if w_headers is not None and not isinstance(w_headers, dict):
                                errors.append(
                                    ValidationIssue(
                                        field=f"{w_prefix}.headers",
                                        message=f"Webhook '{w_id}' headers must be a dictionary.",
                                        level=ValidationLevel.ERROR.value,
                                    )
                                )

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            infos=infos,
        )
