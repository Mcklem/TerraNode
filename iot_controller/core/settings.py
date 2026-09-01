import os
import logging
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    """Centralized application settings loaded from environment variables and .env file."""

    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    config_path: str = os.getenv("CONFIG_PATH", "config/system.yaml")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///controller.db")
    mock_nodes: bool = os.getenv("MOCK_NODES", "false").lower() in ("true", "1", "yes")
    log_readings: bool = os.getenv("LOG_READINGS", "true").lower() in ("true", "1", "yes")
    log_rule_evaluations: bool = os.getenv("LOG_RULE_EVALUATIONS", "true").lower() in ("true", "1", "yes")

    # Node default connection settings
    node_arduino_wait: int = int(os.getenv("NODE_ARDUINO_WAIT", "5"))
    node_max_retries: int = int(os.getenv("NODE_MAX_RETRIES", "3"))
    node_timeout: float = float(os.getenv("NODE_TIMEOUT", "12.0"))

    # FastAPI Web Service settings
    enable_api: bool = os.getenv("ENABLE_API", "false").lower() in ("true", "1", "yes")
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))

    def get_log_level_int(self) -> int:
        """Convert log level string to standard logging integer level."""
        return getattr(logging, self.log_level, logging.INFO)


settings = Settings()
