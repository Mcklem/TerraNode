import os
import tempfile
import unittest
from core.config import ConfigLoader, ConfigurationError


class TestConfigLoader(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_yaml(self, content: str) -> str:
        path = os.path.join(self.temp_dir.name, "test_system.yaml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_valid_config_with_nested_node_devices(self):
        yaml_content = """
nodes:
  weather_01:
    driver: mock
    host: 127.0.0.1
    port: 3030
    enabled: true
    devices:
      light_01:
        type: ldr
        pin: A0
        poll_interval: 10
      env_01:
        type: bmp180
        bus: i2c
        address: 0x77
"""
        filepath = self._write_yaml(yaml_content)
        loader = ConfigLoader(filepath)
        config = loader.load()

        self.assertIn("nodes", config)
        self.assertIn("devices", config)
        self.assertIn("light_01", config["devices"])
        self.assertIn("env_01", config["devices"])
        self.assertEqual(config["devices"]["light_01"]["node"], "weather_01")
        self.assertEqual(config["devices"]["env_01"]["node"], "weather_01")

    def test_duplicate_device_id_raises_error(self):
        yaml_content = """
nodes:
  node_01:
    driver: mock
    host: 127.0.0.1
    devices:
      sensor_01:
        type: ldr
        pin: A0
  node_02:
    driver: mock
    host: 127.0.0.1
    devices:
      sensor_01:
        type: soil_moisture
        pin: A0
"""
        filepath = self._write_yaml(yaml_content)
        loader = ConfigLoader(filepath)
        with self.assertRaises(ConfigurationError):
            loader.load()

    def test_environment_variable_interpolation(self):
        os.environ["TEST_NODE_HOST"] = "192.168.1.99"
        os.environ["TEST_AUTH_KEY"] = "super_secret_123"
        try:
            yaml_content = """
nodes:
  node_01:
    driver: mock
    host: ${TEST_NODE_HOST}
    auth_key: ${TEST_AUTH_KEY:-fallback_key}
    port: ${TEST_PORT:-3030}
devices: {}
"""
            filepath = self._write_yaml(yaml_content)
            loader = ConfigLoader(filepath)
            config = loader.load()

            self.assertEqual(config["nodes"]["node_01"]["host"], "192.168.1.99")
            self.assertEqual(config["nodes"]["node_01"]["auth_key"], "super_secret_123")
            self.assertEqual(config["nodes"]["node_01"]["port"], 3030)
        finally:
            os.environ.pop("TEST_NODE_HOST", None)
            os.environ.pop("TEST_AUTH_KEY", None)

    def test_missing_file_raises_error(self):
        loader = ConfigLoader("non_existent_file.yaml")
        with self.assertRaises(ConfigurationError):
            loader.load()

    def test_invalid_node_reference_raises_error(self):
        yaml_content = """
nodes:
  node_01:
    driver: mock
    host: 127.0.0.1
devices:
  sensor_01:
    type: ldr
    node: non_existent_node
    pin: A0
"""
        filepath = self._write_yaml(yaml_content)
        loader = ConfigLoader(filepath)
        with self.assertRaises(ConfigurationError):
            loader.load()


if __name__ == "__main__":
    unittest.main()
