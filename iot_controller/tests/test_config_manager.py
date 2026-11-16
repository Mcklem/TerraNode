import os
import shutil
import tempfile
import unittest
from config_manager.backup_manager import BackupManager
from config_manager.diff_engine import DiffEngine
from config_manager.models import ValidationLevel
from config_manager.service import (
    ConfigManagerService,
    ConfigurationConflictError,
    ConfigurationSaveError,
)
from config_manager.validator import ConfigValidator
from config_manager.yaml_parser import (
    MASKED_SECRET_SENTINEL,
    mask_secrets,
    parse_yaml,
    serialize_yaml,
    to_plain_dict,
    unmask_secrets,
)


class TestConfigManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.test_dir, "system.yaml")
        self.backups_dir = os.path.join(self.test_dir, "backups")

        # Create a sample system.yaml with comments
        self.sample_yaml = """# ==============================================================================
# SAMPLE TERRANODE CONFIGURATION
# ==============================================================================
system:
  name: test_parcela
  version: "1.0"
  database: "controller.db"
  log_readings: true
  log_rule_evaluations: true

nodes:
  node_one:
    driver: secure_standard_firmata_wifi
    auth_key: super_secret_node_key_123
    host: 192.168.1.100
    port: 3030
    enabled: true
    devices:
      soil_01:
        type: soil_moisture
        pin: A0                   # Analog moisture pin
        poll_interval: 30
        calibration:
          dry: 900
          wet: 350
      pump_01:
        type: relay
        pin: D5                   # Water pump relay
        active_low: true

rules:
  irrigation_rule:
    enabled: true
    condition:
      device: soil_01
      property: value
      operator: "<"
      value: 30
    actions:
      - device: pump_01
        command: turn_on

schedules:
  daily_pump:
    enabled: true
    device: pump_01
    command: turn_on
    stop_command: turn_off
    time: "08:00"
    duration: 300
"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write(self.sample_yaml)

        self.service = ConfigManagerService(self.config_path, self.backups_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_yaml_roundtrip_preserves_comments(self):
        """Verify ruamel.yaml preserves explanatory comments and structure."""
        parsed, err, _ = parse_yaml(self.sample_yaml)
        self.assertIsNone(err)
        dumped = serialize_yaml(parsed)

        self.assertIn("# SAMPLE TERRANODE CONFIGURATION", dumped)
        self.assertIn("# Analog moisture pin", dumped)
        self.assertIn("# Water pump relay", dumped)

    def test_secret_masking_and_unmasking(self):
        """Verify auth_key is masked in visual representation and restored on save."""
        parsed, _, _ = parse_yaml(self.sample_yaml)
        masked = mask_secrets(parsed)

        node_cfg = masked["nodes"]["node_one"]
        self.assertEqual(node_cfg["auth_key"], MASKED_SECRET_SENTINEL)

        # Unmasking with original restores the secret
        restored = unmask_secrets(masked, parsed)
        self.assertEqual(
            restored["nodes"]["node_one"]["auth_key"], "super_secret_node_key_123"
        )

        # If user explicitly provides a new secret, it replaces the old one
        masked_modified = dict(masked)
        masked_modified["nodes"]["node_one"]["auth_key"] = "brand_new_secret_key"
        restored_new = unmask_secrets(masked_modified, parsed)
        self.assertEqual(
            restored_new["nodes"]["node_one"]["auth_key"], "brand_new_secret_key"
        )

    def test_validation_success_on_valid_yaml(self):
        """Verify valid sample YAML passes all validation levels."""
        val_res = self.service.validate(self.sample_yaml)
        self.assertTrue(val_res.valid)
        self.assertEqual(len(val_res.errors), 0)

    def test_validation_syntax_error(self):
        """Verify Level 1 syntax error detection with line numbers."""
        invalid_yaml = "system:\n  name: test\n  invalid_mapping"
        val_res = self.service.validate(invalid_yaml)
        self.assertFalse(val_res.valid)
        self.assertGreater(len(val_res.errors), 0)
        self.assertEqual(val_res.errors[0].field, "yaml_syntax")

    def test_validation_pin_conflict(self):
        """Verify Level 3 detects GPIO pin conflicts on the same node."""
        bad_yaml = self.sample_yaml.replace("pin: D5", "pin: A0")
        val_res = self.service.validate(bad_yaml)
        self.assertFalse(val_res.valid)
        err_messages = [e.message for e in val_res.errors]
        self.assertTrue(any("Pin conflict" in m or "cannot be assigned" in m for m in err_messages))

    def test_validation_nonexistent_reference(self):
        """Verify references to non-existent devices in rules/schedules are flagged."""
        bad_yaml = self.sample_yaml.replace("device: pump_01", "device: non_existent_actuator")
        val_res = self.service.validate(bad_yaml)
        self.assertFalse(val_res.valid)
        self.assertTrue(any("non_existent_actuator" in e.message for e in val_res.errors))

    def test_validation_invalid_cron(self):
        """Verify invalid cron pattern detection."""
        bad_yaml = self.sample_yaml.replace('time: "08:00"', 'cron: "99 99 99 99 99"')
        val_res = self.service.validate(bad_yaml)
        self.assertFalse(val_res.valid)
        self.assertTrue(any("cron error" in e.message for e in val_res.errors))

    def test_diff_engine_redacts_secrets(self):
        """Verify diff engine does not expose plaintext secrets."""
        modified_yaml = self.sample_yaml.replace("host: 192.168.1.100", "host: 192.168.1.200")
        diff_res = DiffEngine.generate_diff(self.sample_yaml, modified_yaml)
        self.assertTrue(diff_res.has_changes)
        self.assertIn("+    host: 192.168.1.200", diff_res.unified_diff)
        self.assertNotIn("super_secret_node_key_123", diff_res.unified_diff)

    def test_transactional_save_and_backup(self):
        """Verify save creates backup, updates file atomically, and preserves comments."""
        initial_checksum = self.service.get_file_checksum()
        modified_yaml = self.sample_yaml.replace("name: test_parcela", "name: parcela_actualizada")

        success, new_checksum, backup_meta, diff_res = self.service.save_raw_yaml(
            modified_yaml,
            base_checksum=initial_checksum,
            author="tester",
            description="Update installation name",
        )

        self.assertTrue(success)
        self.assertNotEqual(initial_checksum, new_checksum)
        self.assertIsNotNone(backup_meta)

        # Verify active file on disk has updated content and comments
        with open(self.config_path, "r", encoding="utf-8") as f:
            updated_content = f.read()

        self.assertIn("name: parcela_actualizada", updated_content)
        self.assertIn("# SAMPLE TERRANODE CONFIGURATION", updated_content)
        self.assertIn("# Analog moisture pin", updated_content)

        # Verify backup exists
        backups = self.service.backup_mgr.list_backups()
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].author, "tester")

    def test_conflict_detection(self):
        """Verify save fails with ConfigurationConflictError when base_checksum mismatches."""
        mismatched_checksum = "a" * 64
        with self.assertRaises(ConfigurationConflictError):
            self.service.save_raw_yaml(
                self.sample_yaml,
                base_checksum=mismatched_checksum,
            )

    def test_rollback_restore_backup(self):
        """Verify restoring a backup restores original configuration cleanly."""
        initial_checksum = self.service.get_file_checksum()

        # Make an edit and save
        modified_yaml = self.sample_yaml.replace("poll_interval: 30", "poll_interval: 60")
        _, _, backup_meta, _ = self.service.save_raw_yaml(
            modified_yaml,
            base_checksum=initial_checksum,
        )

        # Confirm edit is on disk
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.assertIn("poll_interval: 60", f.read())

        # Perform rollback
        success, restored_checksum, _ = self.service.restore_backup(backup_meta.id)
        self.assertTrue(success)
        self.assertEqual(restored_checksum, initial_checksum)

        # Confirm original is restored on disk
        with open(self.config_path, "r", encoding="utf-8") as f:
            restored_content = f.read()
        self.assertIn("poll_interval: 30", restored_content)

    def test_visual_model_save_and_comment_preservation(self):
        """Verify saving from visual model preserves comments and updates values."""
        initial_checksum = self.service.get_file_checksum()
        visual_model = self.service.load_active_config(mask=True)

        # Modify values in visual model
        visual_model["system"]["name"] = "visual_saved_parcela"
        visual_model["devices"]["soil_01"]["poll_interval"] = 45

        # Add a new relay device to node_one
        visual_model["devices"]["valve_01"] = {
            "type": "relay",
            "node": "node_one",
            "pin": "D6",
            "active_low": True,
        }

        success, new_checksum, backup_meta, diff_res = self.service.save_visual_model(
            visual_model,
            base_checksum=initial_checksum,
            author="visual_user",
            description="Visual edit adding valve",
        )

        self.assertTrue(success)
        self.assertNotEqual(initial_checksum, new_checksum)

        # Verify on disk
        with open(self.config_path, "r", encoding="utf-8") as f:
            updated_content = f.read()

        self.assertIn("name: visual_saved_parcela", updated_content)
        self.assertIn("poll_interval: 45", updated_content)
        self.assertIn("valve_01:", updated_content)
        self.assertIn("# SAMPLE TERRANODE CONFIGURATION", updated_content)
        self.assertIn("# Analog moisture pin", updated_content)

    def test_path_traversal_protection(self):
        """Verify backup ID cannot traverse directories."""
        with self.assertRaises(ValueError):
            self.service.backup_mgr.get_backup("../../etc/passwd")

    def test_hex_scalar_and_address_preservation(self):
        """Verify hexadecimal I2C addresses like '0x77' are preserved as hex (not converted to 119)."""
        hex_yaml = """system:
  name: hex_test
  version: "1.0"
nodes:
  node_one:
    driver: mock
    devices:
      env_sensor:
        type: bmp180
        bus: i2c
        address: 0x77
        poll_interval: 10
rules: {}
schedules: {}
"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write(hex_yaml)

        # 1. Load active config -> address should be formatted as "0x77" in plain dict
        loaded = self.service.load_active_config(mask=True)
        self.assertEqual(loaded["devices"]["env_sensor"]["address"], "0x77")

        # 2. Diff without modifications should be completely empty (no unwanted 0x77 -> 119 diff)
        _, diff_res = self.service.generate_diff_for_visual_model(loaded)
        self.assertFalse(diff_res.has_changes)
        self.assertEqual(diff_res.unified_diff.strip(), "")

        # 3. Save without changing address -> on disk it must remain unquoted 0x77
        self.service.save_visual_model(loaded)
        with open(self.config_path, "r", encoding="utf-8") as f:
            disk_content = f.read()
        self.assertIn("address: 0x77", disk_content)
        self.assertNotIn("address: 119", disk_content)
        self.assertNotIn("address: '0x77'", disk_content)

        # 4. Modify address to 0x76 in visual model
        loaded["devices"]["env_sensor"]["address"] = "0x76"
        _, diff_mod = self.service.generate_diff_for_visual_model(loaded)
        self.assertTrue(diff_mod.has_changes)
        self.assertIn("-        address: 0x77", diff_mod.unified_diff)
        self.assertIn("+        address: 0x76", diff_mod.unified_diff)

        # 5. Save modified address -> on disk it must be 0x76
        self.service.save_visual_model(loaded)
        with open(self.config_path, "r", encoding="utf-8") as f:
            saved_content = f.read()
        self.assertIn("address: 0x76", saved_content)


if __name__ == "__main__":
    unittest.main()
