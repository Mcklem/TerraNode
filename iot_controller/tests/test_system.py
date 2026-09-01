import os
import tempfile
import unittest
from core.system import ControllerSystem


class TestControllerSystem(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.config_path = os.path.join(self.temp_dir.name, "system.yaml")
        db_path = os.path.join(self.temp_dir.name, "test_system.db").replace("\\", "/")

        yaml_content = f"""
system:
  name: test_controller
  version: "1.0"
  database: "{db_path}"

nodes:
  n1:
    driver: mock
    host: 127.0.0.1
    port: 3030
    enabled: true

devices:
  ldr_01:
    type: ldr
    node: n1
    pin: A0
    poll_interval: 1

  pump_01:
    type: relay
    node: n1
    pin: D5
    active_low: true

rules:
  auto_pump:
    enabled: true
    condition:
      device: ldr_01
      property: value
      operator: "<"
      value: 100
    actions:
      - device: pump_01
        command: turn_on
"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)

    async def asyncTearDown(self):
        self.temp_dir.cleanup()

    async def test_full_system_lifecycle(self):
        from core.settings import settings
        prev_enable = settings.enable_api
        settings.enable_api = False
        try:
            system = ControllerSystem(self.config_path)
            await system.start()

            self.assertTrue(system._running)
            health = system.health_monitor.get_system_health()

            self.assertIn("nodes", health)
            self.assertIn("n1", health["nodes"])
            self.assertEqual(health["nodes"]["n1"]["status"], "CONNECTED")

            self.assertIn("devices", health)
            self.assertIn("ldr_01", health["devices"])
            self.assertIn("pump_01", health["devices"])

            await system.stop()
            self.assertFalse(system._running)
        finally:
            settings.enable_api = prev_enable

    async def test_system_with_api_enabled(self):
        from core.settings import settings
        settings.enable_api = True
        settings.api_port = 8899  # avoid port conflict
        try:
            system = ControllerSystem(self.config_path)
            await system.start()
            self.assertTrue(system._running)
            self.assertIsNotNone(system.api_task)
            self.assertIsNotNone(system.live_command_service)
            await system.stop()
        finally:
            settings.enable_api = False


if __name__ == "__main__":
    unittest.main()
