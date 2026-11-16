import hashlib
import os
import shutil
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from config_manager.backup_manager import BackupManager
from config_manager.diff_engine import DiffEngine
from config_manager.models import (
    BackupMetadata,
    ConfigStatus,
    DiffResult,
    ValidationResult,
)
from config_manager.validator import (
    ACTUATOR_COMMANDS,
    SENSOR_PROPERTIES,
    VALID_DRIVERS,
    VALID_OPERATORS,
    ConfigValidator,
)
from config_manager.yaml_parser import (
    MASKED_SECRET_SENTINEL,
    apply_visual_model_to_commented_map,
    create_yaml_engine,
    mask_secrets,
    normalize_devices,
    parse_yaml,
    restore_masked_secrets_in_commented_map,
    serialize_yaml,
    to_plain_dict,
    unmask_secrets,
)
from core.registry import DEVICE_REGISTRY
from nodes.base_node import NODEMCU_PIN_MAP
from utils.logging import get_logger


class ConfigurationConflictError(Exception):
    """Raised when active configuration was modified externally while being edited."""
    pass


class ConfigurationSaveError(Exception):
    """Raised when configuration validation or file write fails."""
    pass


class ConfigManagerService:
    """
    Central service orchestrating TerraNode configuration lifecycle:
    parsing, comment-preserving roundtrips, multi-level validation,
    conflict detection, atomic transactional saving, backups, and rollback.
    """

    def __init__(self, config_path: str, backups_dir: Optional[str] = None):
        self.config_path = os.path.abspath(config_path)
        if backups_dir:
            self.backups_dir = os.path.abspath(backups_dir)
        else:
            config_dir = os.path.dirname(self.config_path)
            self.backups_dir = os.path.join(config_dir, "backups")

        self.backup_mgr = BackupManager(self.backups_dir)
        self.logger = get_logger("ConfigManager")
        self.last_saved_at: Optional[str] = None
        self.last_applied_at: Optional[str] = None
        self.runtime_checksum: Optional[str] = None

    def get_file_checksum(self, path: Optional[str] = None) -> str:
        """Compute SHA-256 hash of configuration file on disk with normalized newlines."""
        target = path or self.config_path
        if not os.path.exists(target):
            return ""
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            content = f.read().replace("\r\n", "\n").replace("\r", "\n")
            return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def get_content_checksum(self, content: str) -> str:
        """Compute SHA-256 hash of string content with normalized newlines."""
        norm = content.replace("\r\n", "\n").replace("\r", "\n")
        return hashlib.sha256(norm.encode("utf-8")).hexdigest()

    def read_raw_yaml(self) -> str:
        """Read the raw configuration file from disk with normalized newlines."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found at: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read().replace("\r\n", "\n").replace("\r", "\n")

    def load_active_config(self, mask: bool = True) -> Dict[str, Any]:
        """
        Load and normalize active configuration.
        Returns dictionary containing system, nodes, devices, rules, schedules.
        """
        content = self.read_raw_yaml()
        from core.config import interpolate_env_vars
        interpolated = interpolate_env_vars(content)
        parsed, err, _ = parse_yaml(interpolated)
        if err or parsed is None:
            raise ConfigurationSaveError(f"Error reading active configuration: {err}")

        plain = to_plain_dict(parsed)
        normalized = normalize_devices(plain)
        if mask:
            normalized = mask_secrets(normalized)
        return normalized

    def get_status(self) -> ConfigStatus:
        """Inspect current configuration status, checksums, synchronization, and validation."""
        raw_yaml = self.read_raw_yaml() if os.path.exists(self.config_path) else ""
        saved_checksum = self.get_content_checksum(raw_yaml) if raw_yaml else ""
        validation = ConfigValidator.validate_yaml_string(raw_yaml) if raw_yaml else ValidationResult(valid=False)

        parsed, _, _ = parse_yaml(raw_yaml)
        plain = to_plain_dict(parsed) if parsed else {}
        norm = normalize_devices(plain)

        counts = {
            "nodes": len(norm.get("nodes", {})),
            "devices": len(norm.get("devices", {})),
            "rules": len(norm.get("rules", {})),
            "schedules": len(norm.get("schedules", {})),
        }

        is_sync = (
            self.runtime_checksum is not None
            and self.runtime_checksum == saved_checksum
        )

        return ConfigStatus(
            active_config_path=self.config_path,
            saved_checksum=saved_checksum,
            runtime_checksum=self.runtime_checksum,
            is_synchronized=is_sync,
            last_saved_at=self.last_saved_at,
            last_applied_at=self.last_applied_at,
            counts=counts,
            validation=validation,
        )

    def validate(self, yaml_content_or_dict: Union[str, Dict[str, Any]]) -> ValidationResult:
        """Validate either a raw YAML string or a structured configuration dictionary."""
        if isinstance(yaml_content_or_dict, str):
            return ConfigValidator.validate_yaml_string(yaml_content_or_dict)
        return ConfigValidator.validate_dict(yaml_content_or_dict)

    def generate_diff(self, proposed_yaml: str) -> DiffResult:
        """Generate diff between active saved configuration and proposed YAML."""
        current_yaml = self.read_raw_yaml() if os.path.exists(self.config_path) else ""
        return DiffEngine.generate_diff(current_yaml, proposed_yaml)

    def generate_diff_for_visual_model(self, visual_model: Dict[str, Any]) -> Tuple[str, DiffResult]:
        """
        Merge visual model with current CommentedMap to generate proposed YAML string and diff.
        Returns: (proposed_yaml_str, DiffResult)
        """
        current_raw = self.read_raw_yaml() if os.path.exists(self.config_path) else ""
        parsed_orig, err, _ = parse_yaml(current_raw)
        if err or parsed_orig is None:
            parsed_orig = CommentedMap()

        updated_map = apply_visual_model_to_commented_map(
            target_map=parsed_orig,
            visual_model=visual_model,
            original_reference=to_plain_dict(parsed_orig),
        )
        proposed_yaml = serialize_yaml(updated_map)
        diff = DiffEngine.generate_diff(current_raw, proposed_yaml)
        return proposed_yaml, diff

    def visual_model_to_yaml(self, visual_model: Dict[str, Any]) -> str:
        """Convert visual model to comment-preserving YAML string."""
        current_raw = self.read_raw_yaml() if os.path.exists(self.config_path) else ""
        parsed_orig, err, _ = parse_yaml(current_raw)
        if err or parsed_orig is None:
            parsed_orig = CommentedMap()

        updated_map = apply_visual_model_to_commented_map(
            target_map=parsed_orig,
            visual_model=visual_model,
            original_reference=to_plain_dict(parsed_orig),
        )
        return serialize_yaml(updated_map)

    def save_raw_yaml(
        self,
        new_yaml_content: str,
        base_checksum: Optional[str] = None,
        author: str = "operator",
        description: str = "Manual YAML edit",
    ) -> Tuple[bool, str, BackupMetadata, DiffResult]:
        """
        Transactional save of raw YAML string.
        1. Conflict check against base_checksum.
        2. Unmask secrets from original file if user retained sentinels.
        3. Multi-level validation.
        4. Generate diff.
        5. Create timestamped backup of current file.
        6. Atomic replacement via temporary file.
        """
        current_raw = self.read_raw_yaml() if os.path.exists(self.config_path) else ""
        current_checksum = self.get_content_checksum(current_raw) if current_raw else ""

        # Conflict check
        if base_checksum and current_checksum and base_checksum != current_checksum:
            raise ConfigurationConflictError(
                "Conflict detected: The configuration file has been modified externally "
                "since you began editing. Please reload the latest version before saving."
            )

        # Unmask secrets if sentinels are present
        parsed_new, err, _ = parse_yaml(new_yaml_content)
        if err or parsed_new is None:
            raise ConfigurationSaveError(f"YAML Syntax Error: {err}")

        parsed_orig, _, _ = parse_yaml(current_raw) if current_raw else (None, None, None)
        if parsed_orig:
            restore_masked_secrets_in_commented_map(parsed_new, parsed_orig)
        final_yaml_to_write = serialize_yaml(parsed_new)

        # Validate proposed configuration
        val_res = ConfigValidator.validate_yaml_string(final_yaml_to_write)
        if not val_res.valid:
            error_msgs = "; ".join([e.message for e in val_res.errors])
            raise ConfigurationSaveError(f"Validation failed: {error_msgs}")

        # Generate diff
        diff_res = DiffEngine.generate_diff(current_raw, final_yaml_to_write)

        # Create backup of current configuration before overwriting
        backup_meta = self.backup_mgr.create_backup(
            yaml_content=current_raw,
            author=author,
            description=description,
            diff_summary={
                "added": diff_res.added_keys,
                "removed": diff_res.removed_keys,
                "modified": diff_res.modified_keys,
            },
        )

        # Write to temporary file in same directory for atomic rename
        config_dir = os.path.dirname(self.config_path)
        temp_file = os.path.join(config_dir, f".{os.path.basename(self.config_path)}.tmp")

        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(final_yaml_to_write)
                f.flush()
                os.fsync(f.fileno())

            # Validate temporary file
            with open(temp_file, "r", encoding="utf-8") as f:
                temp_content = f.read()
            temp_val = ConfigValidator.validate_yaml_string(temp_content)
            if not temp_val.valid:
                raise ConfigurationSaveError("Temporary file validation failed prior to replacement.")

            # Atomic replace
            os.replace(temp_file, self.config_path)

        except Exception as e:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
            raise ConfigurationSaveError(f"Failed to replace active configuration file: {e}")

        new_checksum = self.get_file_checksum()
        self.last_saved_at = datetime.now().isoformat()
        self.logger.info(f"Configuration saved successfully (Checksum: {new_checksum[:8]}, Backup: {backup_meta.id})")

        return True, new_checksum, backup_meta, diff_res

    def save_visual_model(
        self,
        visual_model: Dict[str, Any],
        base_checksum: Optional[str] = None,
        author: str = "operator",
        description: str = "Visual configuration edit",
    ) -> Tuple[bool, str, BackupMetadata, DiffResult]:
        """
        Save configuration modified through the visual editor.
        Merges visual model into the current CommentedMap to preserve comments and structure.
        """
        current_raw = self.read_raw_yaml() if os.path.exists(self.config_path) else ""
        current_checksum = self.get_content_checksum(current_raw) if current_raw else ""

        if base_checksum and current_checksum and base_checksum != current_checksum:
            raise ConfigurationConflictError(
                "Conflict detected: The configuration file has been modified externally "
                "since you began editing. Please reload the latest version before saving."
            )

        parsed_orig, err, _ = parse_yaml(current_raw)
        if err or parsed_orig is None:
            raise ConfigurationSaveError(f"Error reading existing configuration for visual merge: {err}")

        # Update CommentedMap in-place preserving comments
        updated_map = apply_visual_model_to_commented_map(
            target_map=parsed_orig,
            visual_model=visual_model,
            original_reference=to_plain_dict(parsed_orig),
        )
        new_yaml_str = serialize_yaml(updated_map)

        return self.save_raw_yaml(
            new_yaml_content=new_yaml_str,
            base_checksum=base_checksum,
            author=author,
            description=description,
        )

    def restore_backup(
        self,
        backup_id: str,
        author: str = "operator",
    ) -> Tuple[bool, str, BackupMetadata]:
        """
        Restore configuration to a previous backup version.
        Validates backup, takes a recovery snapshot of current configuration, and replaces atomically.
        """
        backup_yaml, backup_meta = self.backup_mgr.get_backup(backup_id)

        # Validate backup YAML before applying
        val_res = ConfigValidator.validate_yaml_string(backup_yaml)
        if not val_res.valid:
            error_msgs = "; ".join([e.message for e in val_res.errors])
            raise ConfigurationSaveError(f"Cannot restore invalid backup '{backup_id}': {error_msgs}")

        # Take backup of current configuration before restoring
        current_raw = self.read_raw_yaml() if os.path.exists(self.config_path) else ""
        pre_restore_backup = self.backup_mgr.create_backup(
            yaml_content=current_raw,
            author=author,
            description=f"Snapshot before rollback to {backup_id}",
        )

        # Atomic replace with backup content
        config_dir = os.path.dirname(self.config_path)
        temp_file = os.path.join(config_dir, f".{os.path.basename(self.config_path)}.tmp")

        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(backup_yaml)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_file, self.config_path)
        except Exception as e:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
            raise ConfigurationSaveError(f"Failed to restore backup: {e}")

        new_checksum = self.get_file_checksum()
        self.last_saved_at = datetime.now().isoformat()
        self.logger.info(f"Restored configuration from backup '{backup_id}' (Checksum: {new_checksum[:8]})")
        return True, new_checksum, pre_restore_backup

    def get_schema_metadata(self) -> Dict[str, Any]:
        """Return dynamic metadata describing drivers, device types, pins, commands, and properties."""
        registered_types = list(DEVICE_REGISTRY._registry.keys())

        device_specs = {}
        for dtype in registered_types:
            category = "sensor" if dtype in ("ldr", "bmp180", "soil_moisture") else "actuator"
            cmds = sorted(list(ACTUATOR_COMMANDS.get(dtype, [])))
            props = sorted(list(SENSOR_PROPERTIES.get(dtype, [])))

            device_specs[dtype] = {
                "type": dtype,
                "category": category,
                "commands": cmds,
                "properties": props,
                "bus": "i2c" if dtype == "bmp180" else "pin",
                "default_pin": "A0" if category == "sensor" and dtype != "bmp180" else ("D5" if dtype == "relay" else "D6"),
            }

        return {
            "supported_drivers": sorted(list(VALID_DRIVERS)),
            "supported_device_types": registered_types,
            "device_specs": device_specs,
            "available_pins": sorted(list(NODEMCU_PIN_MAP.keys())),
            "comparison_operators": sorted(list(VALID_OPERATORS)),
            "notification_channels": ["email", "telegram", "webhook", "all"],
            "webhook_methods": ["GET", "POST", "PUT"],
        }
