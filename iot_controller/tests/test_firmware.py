import os
import shutil
import tempfile
import unittest
from fastapi.testclient import TestClient
from api.app import create_app
from api.dependencies import system_container
from firmware.catalog import FirmwareCatalog
from firmware.compilation.mock_driver import MockCompilerDriver
from firmware.engine import TemplateEngine, sanitize_cpp_string
from firmware.manifest import (
    BoardProfile,
    FirmwareManifest,
    FirmwareParameter,
    validate_parameter_value,
    validate_user_parameters,
)
from firmware.repository import FirmwareRepository
from firmware.service import FirmwareService
from firmware.workspace import WorkspaceManager
from storage.database import Database


class TestFirmwareStudio(unittest.IsolatedAsyncioTestCase):
    """Unit and integration test suite for TerraNode Firmware Studio."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_firmware.db").replace("\\", "/")
        self.db = Database(f"sqlite:///{self.db_path}")

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def asyncSetUp(self):
        await self.db.initialize()

    def test_parameter_validation_types(self):
        """Test strict validation of different parameter types."""
        # String parameter
        p_str = FirmwareParameter(id="NAME", label="Name", type="string", min_length=3, max_length=10)
        self.assertEqual(validate_parameter_value(p_str, "NodeMCU"), "NodeMCU")
        with self.assertRaises(ValueError):
            validate_parameter_value(p_str, "ab")
        with self.assertRaises(ValueError):
            validate_parameter_value(p_str, "very_long_name_exceeding_limit")

        # IP address parameter
        p_ip = FirmwareParameter(id="IP", label="Server IP", type="ip")
        self.assertEqual(validate_parameter_value(p_ip, "192.168.1.100"), "192.168.1.100")
        with self.assertRaises(ValueError):
            validate_parameter_value(p_ip, "999.999.999.999")
        with self.assertRaises(ValueError):
            validate_parameter_value(p_ip, "not_an_ip")

        # Port parameter
        p_port = FirmwareParameter(id="PORT", label="Port", type="port")
        self.assertEqual(validate_parameter_value(p_port, "3030"), 3030)
        self.assertEqual(validate_parameter_value(p_port, 80), 80)
        with self.assertRaises(ValueError):
            validate_parameter_value(p_port, 70000)
        with self.assertRaises(ValueError):
            validate_parameter_value(p_port, -1)

        # Number parameter
        p_num = FirmwareParameter(id="NUM", label="Interval", type="number", min=10, max=100)
        self.assertEqual(validate_parameter_value(p_num, 50), 50)
        with self.assertRaises(ValueError):
            validate_parameter_value(p_num, 5)
        with self.assertRaises(ValueError):
            validate_parameter_value(p_num, 200)

        # Boolean parameter
        p_bool = FirmwareParameter(id="ACTIVE", label="Active", type="boolean")
        self.assertTrue(validate_parameter_value(p_bool, "true"))
        self.assertTrue(validate_parameter_value(p_bool, "1"))
        self.assertFalse(validate_parameter_value(p_bool, "false"))
        self.assertFalse(validate_parameter_value(p_bool, "0"))

        # Select parameter
        from firmware.manifest import ParameterOption
        p_sel = FirmwareParameter(
            id="MODE",
            label="Mode",
            type="select",
            options=[ParameterOption(value="0", label="Zero"), ParameterOption(value="1", label="One")],
        )
        self.assertEqual(validate_parameter_value(p_sel, "1"), "1")
        with self.assertRaises(ValueError):
            validate_parameter_value(p_sel, "2")

    def test_cpp_string_sanitization(self):
        """Test escaping of dangerous characters in C++ macro substitutions."""
        injection_attempt = 'secret"; system("reboot"); //'
        sanitized = sanitize_cpp_string(injection_attempt)
        self.assertEqual(sanitized, 'secret\\"; system(\\"reboot\\"); //')

        newlines_attempt = "line1\nline2\rline3\\path"
        sanitized2 = sanitize_cpp_string(newlines_attempt)
        self.assertEqual(sanitized2, "line1\\nline2\\rline3\\\\path")

    def test_catalog_discovery(self):
        """Test discovering templates in iot_hardware/firmware/templates."""
        catalog = FirmwareCatalog()
        manifests = catalog.list_manifests()
        self.assertGreaterEqual(len(manifests), 2)

        template_ids = [m.id for m in manifests]
        self.assertIn("secure_firmata_wifi", template_ids)
        self.assertIn("standard_firmata_wifi", template_ids)

        secure_m = catalog.get_manifest("secure_firmata_wifi")
        self.assertIsNotNone(secure_m)
        self.assertEqual(secure_m.board.fqbn, "esp8266:esp8266:nodemcuv2")

        readme = catalog.get_readme("secure_firmata_wifi")
        self.assertIsNotNone(readme)
        self.assertIn("Autenticación Sysex", readme)

    def test_template_engine_generation(self):
        """Test generating configured files and placeholder replacement."""
        catalog = FirmwareCatalog()
        template_dir = catalog.get_template_dir("secure_firmata_wifi")
        self.assertIsNotNone(template_dir)

        output_dir = os.path.join(self.temp_dir, "generated_test")
        engine = TemplateEngine()

        params = {
            "WIFI_SSID": "TerraNet_Guest",
            "WIFI_PASS": 'Secret\\"WPA\\"Pass',
            "NODE_AUTH_KEY": "secure_token_12345",
            "NODE_HOSTNAME": "greenhouse-node-01",
            "SERVER_PORT": 3030,
            "WATCHDOG_TIMEOUT_MS": 8000,
            "USE_TLS_SECURITY": "0",
        }

        files = engine.generate(template_dir, params, output_dir)
        self.assertGreater(len(files), 0)

        # Verify wifiConfig.h substitution
        wificonfig_path = os.path.join(output_dir, "wifiConfig.h")
        self.assertTrue(os.path.isfile(wificonfig_path))
        with open(wificonfig_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('#define SECRET_WIFI_SSID "TerraNet_Guest"', content)
        self.assertIn('#define SECRET_NODE_AUTH_KEY "secure_token_12345"', content)
        self.assertIn("#define SERVER_PORT 3030", content)
        self.assertNotIn("{{WIFI_SSID}}", content)
        self.assertNotIn("{{NODE_AUTH_KEY}}", content)

        # Verify SecureStandardFirmataWiFi.ino watchdog substitution
        ino_path = os.path.join(output_dir, "SecureStandardFirmataWiFi.ino")
        self.assertTrue(os.path.isfile(ino_path))
        with open(ino_path, "r", encoding="utf-8") as f:
            ino_content = f.read()
        self.assertIn("#define WATCHDOG_TIMEOUT_MS         8000", ino_content)

    async def test_repository_and_database(self):
        """Test persisting and querying build records in SQLite."""
        repo = FirmwareRepository(self.db)
        build_id = "test-build-uuid-001"

        record = await repo.create_build(
            build_id=build_id,
            template_id="secure_firmata_wifi",
            template_version="1.2.0",
            target_fqbn="esp8266:esp8266:nodemcuv2",
            public_params={"NODE_HOSTNAME": "test-node", "SERVER_PORT": 3030},
        )
        self.assertEqual(record["id"], build_id)
        self.assertEqual(record["status"], "QUEUED")

        # Update status
        updated = await repo.update_status(
            build_id=build_id,
            status="COMPILED",
            status_message="Compilación exitosa",
            binary_filename="firmware.bin",
            binary_size_bytes=256000,
            checksum_sha256="abcdef123456",
        )
        self.assertEqual(updated["status"], "COMPILED")
        self.assertEqual(updated["binary_filename"], "firmware.bin")

        # Query back
        fetched = await repo.get_build(build_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["checksum_sha256"], "abcdef123456")

        total, builds = await repo.list_builds(limit=10, offset=0)
        self.assertEqual(total, 1)
        self.assertEqual(len(builds), 1)

    async def test_full_service_workflow(self):
        """Test full end-to-end service cycle: validate -> generate -> mock compile."""
        service = FirmwareService(
            database=self.db,
            workspaces_dir=os.path.join(self.temp_dir, "workspaces"),
            compiler_driver=MockCompilerDriver(),
        )

        # 1. Validate
        valid_params = {
            "WIFI_SSID": "MyFarmWiFi",
            "WIFI_PASS": "TopSecretPass123",
            "NODE_AUTH_KEY": "farm_secret_auth_token_3030",
            "NODE_HOSTNAME": "greenhouse-soil",
            "SERVER_PORT": 3030,
            "WATCHDOG_TIMEOUT_MS": 5000,
            "USE_TLS_SECURITY": "0",
        }
        validated = service.validate_config("secure_firmata_wifi", valid_params)
        self.assertEqual(validated["WIFI_SSID"], "MyFarmWiFi")

        # 2. Generate
        build = await service.generate_build("secure_firmata_wifi", valid_params)
        build_id = build["id"]
        self.assertEqual(build["status"], "QUEUED")

        # 3. Source zip creation
        zip_path = service.get_source_zip(build_id)
        self.assertIsNotNone(zip_path)
        self.assertTrue(os.path.isfile(zip_path))

        # 4. Compile with mock driver
        compiled = await service.compile_build(build_id)
        self.assertEqual(compiled["status"], "COMPILED")
        self.assertIsNotNone(compiled["binary_filename"])
        self.assertIsNotNone(compiled["checksum_sha256"])

        # 5. Check binary file exists
        bin_path = service.get_binary_path(build_id)
        self.assertIsNotNone(bin_path)
        self.assertTrue(os.path.isfile(bin_path))


class TestFirmwareApiEndpoints(unittest.TestCase):
    """Test FastAPI REST endpoints for Firmware Studio."""

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        cls.db_path = os.path.join(cls.temp_dir, "test_api_firmware.db").replace("\\", "/")
        cls.db = Database(f"sqlite:///{cls.db_path}")

        import asyncio
        asyncio.run(cls.db.initialize())

        # Configure system_container
        system_container.db = cls.db
        cls.service = FirmwareService(
            database=cls.db,
            workspaces_dir=os.path.join(cls.temp_dir, "api_workspaces"),
            compiler_driver=MockCompilerDriver(),
        )
        system_container.firmware_service = cls.service

        app = create_app()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_api_list_templates(self):
        response = self.client.get("/api/v1/firmware/templates")
        self.assertEqual(response.status_code, 200)
        templates = response.json()
        self.assertGreaterEqual(len(templates), 2)

    def test_api_get_template(self):
        response = self.client.get("/api/v1/firmware/templates/secure_firmata_wifi")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], "secure_firmata_wifi")
        self.assertIn("readme", data)

    def test_api_validate_config(self):
        payload = {
            "parameters": {
                "WIFI_SSID": "FarmWiFi",
                "WIFI_PASS": "ValidPass123",
                "NODE_AUTH_KEY": "valid_token_3030",
                "NODE_HOSTNAME": "node-01",
                "SERVER_PORT": 3030,
                "WATCHDOG_TIMEOUT_MS": 5000,
                "USE_TLS_SECURITY": "0",
            }
        }
        response = self.client.post(
            "/api/v1/firmware/templates/secure_firmata_wifi/validate", json=payload
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["valid"])

    def test_api_generate_and_compile(self):
        payload = {
            "parameters": {
                "WIFI_SSID": "FarmWiFi",
                "WIFI_PASS": "ValidPass123",
                "NODE_AUTH_KEY": "valid_token_3030",
                "NODE_HOSTNAME": "node-01",
                "SERVER_PORT": 3030,
                "WATCHDOG_TIMEOUT_MS": 5000,
                "USE_TLS_SECURITY": "0",
            }
        }
        # Generate
        gen_res = self.client.post(
            "/api/v1/firmware/templates/secure_firmata_wifi/generate", json=payload
        )
        self.assertEqual(gen_res.status_code, 200)
        build_id = gen_res.json()["id"]

        # Compile
        compile_res = self.client.post(
            f"/api/v1/firmware/builds/{build_id}/compile", json={"force_mock": True}
        )
        self.assertEqual(compile_res.status_code, 200)
        self.assertEqual(compile_res.json()["status"], "COMPILED")

        # Download Binary
        bin_res = self.client.get(f"/api/v1/firmware/builds/{build_id}/binary")
        self.assertEqual(bin_res.status_code, 200)
        self.assertEqual(bin_res.headers["content-type"], "application/octet-stream")

        # Download Source
        src_res = self.client.get(f"/api/v1/firmware/builds/{build_id}/source")
        self.assertEqual(src_res.status_code, 200)
        self.assertEqual(src_res.headers["content-type"], "application/zip")

        # History
        hist_res = self.client.get("/api/v1/firmware/history")
        self.assertEqual(hist_res.status_code, 200)
        self.assertGreaterEqual(hist_res.json()["total"], 1)


if __name__ == "__main__":
    unittest.main()
