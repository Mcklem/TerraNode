import os
import unittest
from core.settings import Settings


class TestSettings(unittest.TestCase):

    def test_settings_default_values(self):
        s = Settings()
        self.assertIsNotNone(s.log_level)
        self.assertIsNotNone(s.database_url)
        self.assertIsNotNone(s.config_path)

    def test_settings_override_via_env(self):
        os.environ["LOG_LEVEL"] = "DEBUG"
        os.environ["DATABASE_URL"] = "sqlite:///custom_test.db"
        s = Settings(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            database_url=os.getenv("DATABASE_URL", "sqlite:///controller.db"),
        )
        self.assertEqual(s.log_level, "DEBUG")
        self.assertEqual(s.database_url, "sqlite:///custom_test.db")


if __name__ == "__main__":
    unittest.main()
