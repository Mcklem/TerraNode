import os
import shutil
import tempfile
import pytest

from config_manager.env_manager import (
    EnvSecretManager,
    EnvSecurityError,
    validate_secret_security,
)
from config_manager.service import ConfigManagerService, ConfigurationSaveError


@pytest.fixture
def temp_env_dir():
    temp_dir = tempfile.mkdtemp()
    dotenv_file = os.path.join(temp_dir, ".env")
    with open(dotenv_file, "w", encoding="utf-8") as f:
        f.write("# Initial .env\nENVIRONMENT=development\n")
    yield temp_dir, dotenv_file
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestEnvSecretManager:
    def test_security_validation_crlf_rejection(self):
        # Valid key and value
        validate_secret_security("TELEGRAM_BOT_TOKEN", "valid_token_123")

        # CRLF injection in value should raise EnvSecurityError
        with pytest.raises(EnvSecurityError, match="illegal newline characters"):
            validate_secret_security("TELEGRAM_BOT_TOKEN", "token\r\nEVIL_VAR=hacked")

        with pytest.raises(EnvSecurityError, match="illegal newline characters"):
            validate_secret_security("TELEGRAM_BOT_TOKEN", "token\nhacked")

    def test_security_validation_invalid_var_name(self):
        # Lowercase or invalid characters rejected
        with pytest.raises(EnvSecurityError, match="Invalid environment variable name"):
            validate_secret_security("bad-name", "secret")

        with pytest.raises(EnvSecurityError, match="Invalid environment variable name"):
            validate_secret_security("A" * 65, "secret")

    def test_extract_and_sync_secrets_canonical(self, temp_env_dir):
        _, dotenv_path = temp_env_dir
        mgr = EnvSecretManager(dotenv_path=dotenv_path)

        visual_model = {
            "notifications": {
                "telegram": {
                    "enabled": True,
                    "bot_token": "123456:ABC-DEF",
                    "chat_id": "987654321",
                },
                "email": {
                    "enabled": True,
                    "smtp_host": "smtp.custom.org",
                    "smtp_port": 587,
                    "username": "admin@custom.org",
                    "password": "supersecretmailpass",
                    "from_address": "alerts@custom.org",
                },
            }
        }

        # 1. Preview without commit
        sanitized, env_changes = mgr.extract_and_sync_secrets(visual_model, commit=False)
        assert sanitized["notifications"]["telegram"]["bot_token"] == "${TELEGRAM_BOT_TOKEN}"
        assert sanitized["notifications"]["telegram"]["chat_id"] == "${TELEGRAM_CHAT_ID}"
        assert sanitized["notifications"]["email"]["password"] == "${EMAIL_PASSWORD}"
        assert len(env_changes) >= 5

        # .env should not have been modified yet
        with open(dotenv_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "123456:ABC-DEF" not in content

        # 2. Save with commit=True
        sanitized_committed, committed_changes = mgr.extract_and_sync_secrets(visual_model, commit=True)
        assert sanitized_committed["notifications"]["telegram"]["bot_token"] == "${TELEGRAM_BOT_TOKEN}"

        # .env should now contain the keys
        with open(dotenv_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "TELEGRAM_BOT_TOKEN='123456:ABC-DEF'" in content or 'TELEGRAM_BOT_TOKEN="123456:ABC-DEF"' in content
            assert "987654321" in content
            assert "supersecretmailpass" in content

        # os.environ should be updated in-memory
        assert os.environ.get("TELEGRAM_BOT_TOKEN") == "123456:ABC-DEF"
        assert os.environ.get("EMAIL_PASSWORD") == "supersecretmailpass"

    def test_extract_node_and_webhook_secrets(self, temp_env_dir):
        _, dotenv_path = temp_env_dir
        mgr = EnvSecretManager(dotenv_path=dotenv_path)

        visual_model = {
            "nodes": {
                "node_greenhouse": {
                    "driver": "nodemcu",
                    "auth_key": "gh_secret_key_999",
                }
            },
            "notifications": {
                "webhooks": {
                    "home_assistant": {
                        "url": "http://192.168.1.5:8123/api/webhook/test",
                        "headers": {
                            "Authorization": "Bearer HA_TOKEN_999",
                            "Content-Type": "application/json",  # Not a secret header
                        },
                    }
                }
            },
        }

        sanitized, changes = mgr.extract_and_sync_secrets(visual_model, commit=True)

        assert sanitized["nodes"]["node_greenhouse"]["auth_key"] == "${NODE_GREENHOUSE_AUTH_KEY}"
        assert (
            sanitized["notifications"]["webhooks"]["home_assistant"]["headers"]["Authorization"]
            == "${WEBHOOK_HOME_ASSISTANT_AUTHORIZATION}"
        )
        # Content-Type should not be externalized
        assert (
            sanitized["notifications"]["webhooks"]["home_assistant"]["headers"]["Content-Type"]
            == "application/json"
        )

        with open(dotenv_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "NODE_GREENHOUSE_AUTH_KEY" in content
            assert "gh_secret_key_999" in content
            assert "WEBHOOK_HOME_ASSISTANT_AUTHORIZATION" in content
            assert "HA_TOKEN_999" in content

    def test_masked_and_template_values_not_overwritten(self, temp_env_dir):
        _, dotenv_path = temp_env_dir
        with open(dotenv_path, "a", encoding="utf-8") as f:
            f.write("TELEGRAM_BOT_TOKEN='existing_token_in_env'\n")
        os.environ["TELEGRAM_BOT_TOKEN"] = "existing_token_in_env"

        mgr = EnvSecretManager(dotenv_path=dotenv_path)

        # Model with masked sentinel
        visual_model = {
            "notifications": {
                "telegram": {
                    "enabled": True,
                    "bot_token": "••••••••",
                    "chat_id": "${CUSTOM_TG_CHAT_ID}",
                }
            }
        }

        raw_yaml = """
notifications:
  telegram:
    enabled: true
    bot_token: ${TELEGRAM_BOT_TOKEN}
    chat_id: ${CUSTOM_TG_CHAT_ID}
"""
        sanitized, changes = mgr.extract_and_sync_secrets(
            visual_model, current_raw_yaml=raw_yaml, commit=True
        )

        assert sanitized["notifications"]["telegram"]["bot_token"] == "${TELEGRAM_BOT_TOKEN}"
        assert sanitized["notifications"]["telegram"]["chat_id"] == "${CUSTOM_TG_CHAT_ID}"
        # No new changes should be made to .env
        assert len(changes) == 0
        assert os.environ["TELEGRAM_BOT_TOKEN"] == "existing_token_in_env"


class TestConfigServiceEnvIntegration:
    def test_service_save_visual_model_externalizes_secrets(self, temp_env_dir):
        temp_dir, dotenv_path = temp_env_dir
        yaml_path = os.path.join(temp_dir, "system.yaml")

        initial_yaml = """
system:
  name: "TerraNode Test"
  version: "1.0.0"
notifications:
  telegram:
    enabled: true
    bot_token: ${TELEGRAM_BOT_TOKEN}
    chat_id: ${TELEGRAM_CHAT_ID}
"""
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(initial_yaml)

        service = ConfigManagerService(config_path=yaml_path, dotenv_path=dotenv_path)

        visual_model = {
            "system": {"name": "TerraNode Test", "version": "1.0.0"},
            "notifications": {
                "telegram": {
                    "enabled": True,
                    "bot_token": "999888:NEW_TOKEN_XYZ",
                    "chat_id": "11223344",
                }
            },
            "nodes": {},
            "devices": {},
            "rules": {},
            "schedules": {},
        }

        # 1. Diff preview
        _, diff = service.generate_diff_for_visual_model(visual_model)
        assert diff.has_changes is True
        assert len(diff.env_changes) >= 1

        # 2. Save
        success, checksum, backup_meta, diff_res = service.save_visual_model(visual_model)
        assert success is True
        assert len(diff_res.env_changes) >= 1

        # Check system.yaml on disk: MUST contain ${TELEGRAM_BOT_TOKEN}, NEVER plaintext
        with open(yaml_path, "r", encoding="utf-8") as f:
            saved_yaml = f.read()
            assert "999888:NEW_TOKEN_XYZ" not in saved_yaml
            assert "${TELEGRAM_BOT_TOKEN}" in saved_yaml
            assert "${TELEGRAM_CHAT_ID}" in saved_yaml

        # Check .env on disk: MUST contain the actual secret
        with open(dotenv_path, "r", encoding="utf-8") as f:
            saved_env = f.read()
            assert "999888:NEW_TOKEN_XYZ" in saved_env
            assert "11223344" in saved_env
