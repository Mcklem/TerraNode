import os
import shutil
import tempfile
import unittest
from fastapi.testclient import TestClient
from api.app import create_app
from api.dependencies import system_container
from config_manager.service import ConfigManagerService
from config_manager.yaml_parser import MASKED_SECRET_SENTINEL


class TestApiConfigRoutes(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.test_dir, "system.yaml")
        self.backups_dir = os.path.join(self.test_dir, "backups")

        self.sample_yaml = """system:
  name: api_test_parcela
  version: "1.0"
  database: "controller.db"
  log_readings: true
  log_rule_evaluations: true

nodes:
  node_one:
    driver: secure_standard_firmata_wifi
    auth_key: super_secure_token_456
    host: 192.168.1.105
    port: 3030
    enabled: true
    devices:
      ldr_01:
        type: ldr
        pin: A0
        poll_interval: 15
      pump_01:
        type: relay
        pin: D5
        active_low: true

rules:
  auto_light:
    enabled: true
    condition:
      device: ldr_01
      property: value
      operator: "<"
      value: 100
    actions:
      - device: pump_01
        command: turn_on

schedules:
  pump_morning:
    enabled: true
    device: pump_01
    command: turn_on
    stop_command: turn_off
    time: "07:30"
    duration: 120
"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write(self.sample_yaml)

        self.config_mgr = ConfigManagerService(self.config_path, self.backups_dir)
        system_container.config_manager = self.config_mgr
        system_container.system = None

        self.app = create_app()
        self.client = TestClient(self.app)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_get_config_masked(self):
        """GET /api/v1/config with masked=true masks auth_key."""
        res = self.client.get("/api/v1/config?masked=true")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIn("raw_yaml", data)
        self.assertIn("config", data)
        self.assertIn("status", data)

        node_cfg = data["config"]["nodes"]["node_one"]
        self.assertEqual(node_cfg["auth_key"], MASKED_SECRET_SENTINEL)
        self.assertEqual(data["status"]["counts"]["nodes"], 1)
        self.assertEqual(data["status"]["counts"]["devices"], 2)

    def test_validate_endpoint_valid_and_invalid(self):
        """POST /api/v1/config/validate validates YAML."""
        # Valid YAML
        res = self.client.post("/api/v1/config/validate", json={"raw_yaml": self.sample_yaml})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["valid"])

        # Invalid YAML with pin conflict
        invalid_yaml = self.sample_yaml.replace("pin: D5", "pin: A0")
        res_inv = self.client.post("/api/v1/config/validate", json={"raw_yaml": invalid_yaml})
        self.assertEqual(res_inv.status_code, 200)
        self.assertFalse(res_inv.json()["valid"])
        self.assertGreater(len(res_inv.json()["errors"]), 0)

    def test_diff_endpoint(self):
        """POST /api/v1/config/diff generates clean diff with masked secrets."""
        proposed = self.sample_yaml.replace("poll_interval: 15", "poll_interval: 45")
        res = self.client.post("/api/v1/config/diff", json={"proposed_yaml": proposed})
        self.assertEqual(res.status_code, 200)
        diff_data = res.json()
        self.assertTrue(diff_data["has_changes"])
        self.assertIn("+        poll_interval: 45", diff_data["unified_diff"])
        self.assertNotIn("super_secure_token_456", diff_data["unified_diff"])
        self.assertEqual(diff_data.get("proposed_yaml"), proposed)

    def test_diff_endpoint_with_visual_model(self):
        """POST /api/v1/config/diff with visual_model generates accurate diff and proposed YAML."""
        current_config = self.config_mgr.load_active_config(mask=True)
        current_config["devices"]["ldr_01"]["poll_interval"] = 55
        res = self.client.post("/api/v1/config/diff", json={"visual_model": current_config})
        self.assertEqual(res.status_code, 200)
        diff_data = res.json()
        self.assertTrue(diff_data["has_changes"])
        self.assertIn("modified_keys", diff_data)
        self.assertIn("proposed_yaml", diff_data)
        self.assertIn("poll_interval: 55", diff_data["proposed_yaml"])

    def test_yaml_to_model_endpoint(self):
        """POST /api/v1/config/yaml-to-model converts raw YAML to structured normalized visual config."""
        res = self.client.post("/api/v1/config/yaml-to-model", json={"raw_yaml": self.sample_yaml})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("config", data)
        self.assertEqual(data["config"]["system"]["name"], "api_test_parcela")
        self.assertIn("ldr_01", data["config"]["devices"])

    def test_save_raw_yaml_and_conflict_detection(self):
        """POST /api/v1/config/save transactionally writes new YAML and detects conflicts."""
        initial_checksum = self.config_mgr.get_file_checksum()
        modified = self.sample_yaml.replace("name: api_test_parcela", "name: parcela_guardada")

        # Save success
        res = self.client.post(
            "/api/v1/config/save",
            json={
                "raw_yaml": modified,
                "base_checksum": initial_checksum,
                "author": "tester_agent",
                "description": "API save test",
            },
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertNotEqual(data["checksum"], initial_checksum)

        # Conflict check: saving again with old initial_checksum should 409
        res_conflict = self.client.post(
            "/api/v1/config/save",
            json={
                "raw_yaml": modified,
                "base_checksum": initial_checksum,
            },
        )
        self.assertEqual(res_conflict.status_code, 409)

    def test_save_visual_model(self):
        """POST /api/v1/config/save with visual_model updates configuration."""
        initial_checksum = self.config_mgr.get_file_checksum()
        current_config = self.config_mgr.load_active_config(mask=True)
        current_config["system"]["name"] = "visual_api_parcela"

        res = self.client.post(
            "/api/v1/config/save",
            json={
                "visual_model": current_config,
                "base_checksum": initial_checksum,
                "author": "ui_operator",
            },
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])

        # Check content on disk
        with open(self.config_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("name: visual_api_parcela", content)

    def test_apply_config_endpoint(self):
        """POST /api/v1/config/apply triggers reload."""
        res = self.client.post("/api/v1/config/apply", json={})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])

    def test_backups_lifecycle_and_restore(self):
        """Test listing, inspecting, restoring, and deleting backups."""
        # 1. Trigger a save to generate a backup
        initial_checksum = self.config_mgr.get_file_checksum()
        modified = self.sample_yaml.replace("time: \"07:30\"", "time: \"09:00\"")
        self.client.post(
            "/api/v1/config/save",
            json={"raw_yaml": modified, "base_checksum": initial_checksum, "author": "backup_tester"},
        )

        # 2. List backups
        res_list = self.client.get("/api/v1/config/backups")
        self.assertEqual(res_list.status_code, 200)
        backups = res_list.json()
        self.assertGreaterEqual(len(backups), 1)
        target_backup_id = backups[0]["id"]

        # 3. Inspect backup
        res_detail = self.client.get(f"/api/v1/config/backups/{target_backup_id}")
        self.assertEqual(res_detail.status_code, 200)
        detail = res_detail.json()
        self.assertIn("07:30", detail["raw_yaml"])

        # 4. Restore backup
        res_restore = self.client.post(f"/api/v1/config/backups/{target_backup_id}/restore")
        self.assertEqual(res_restore.status_code, 200)
        self.assertTrue(res_restore.json()["success"])

        # Verify disk restored
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.assertIn("07:30", f.read())

    def test_schema_metadata_endpoint(self):
        """GET /api/v1/config/schema returns supported drivers and device metadata."""
        res = self.client.get("/api/v1/config/schema")
        self.assertEqual(res.status_code, 200)
        schema = res.json()

        self.assertIn("supported_drivers", schema)
        self.assertIn("secure_standard_firmata_wifi", schema["supported_drivers"])
        self.assertIn("supported_device_types", schema)
        self.assertIn("relay", schema["supported_device_types"])
        self.assertIn("available_pins", schema)
        self.assertIn("D5", schema["available_pins"])
        self.assertIn("A0", schema["available_pins"])


if __name__ == "__main__":
    unittest.main()
