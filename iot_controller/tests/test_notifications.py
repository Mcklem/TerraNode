import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from automation.rule_engine import RuleEngine
from config_manager.validator import ConfigValidator
from config_manager.yaml_parser import (
    MASKED_SECRET_SENTINEL,
    apply_visual_model_to_commented_map,
    mask_secrets,
    parse_yaml,
    unmask_secrets,
)
from core.device_manager import DeviceManager
from core.event_bus import Event, EventBus
from core.node_manager import NodeManager
from core.pin_manager import PinManager
from core.registry import DEVICE_REGISTRY
from services.notifications import (
    NotificationChannel,
    NotificationPayload,
    NotificationService,
)
from services.notifications.channels.email import send_email
from services.notifications.channels.telegram import send_telegram
from services.notifications.channels.webhook import send_webhook


class TestNotificationChannels(unittest.IsolatedAsyncioTestCase):

    @patch("services.notifications.channels.email._send_email_sync")
    async def test_email_channel_success(self, mock_send_sync):
        cfg = {
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "use_tls": True,
            "username": "user@example.com",
            "password": "secret_password",
            "from_address": "terranode@example.com",
            "to_addresses": ["admin@example.com"],
        }
        payload = NotificationPayload(
            title="Alerta Test",
            message="Mensaje de prueba",
            channel=NotificationChannel.EMAIL,
        )
        res = await send_email(cfg, payload)
        self.assertTrue(res.success)
        self.assertEqual(res.channel, "email")
        mock_send_sync.assert_called_once()

    async def test_email_channel_missing_host(self):
        cfg = {"to_addresses": ["admin@example.com"]}
        payload = NotificationPayload(message="test", channel=NotificationChannel.EMAIL)
        res = await send_email(cfg, payload)
        self.assertFalse(res.success)
        self.assertIn("smtp_host", res.error)

    @patch("httpx.AsyncClient.post")
    async def test_telegram_channel_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-type": "application/json"}
        mock_resp.json.return_value = {"ok": True, "result": {"message_id": 123}}
        mock_post.return_value = mock_resp

        cfg = {"bot_token": "12345:ABCDEF", "chat_id": "987654"}
        payload = NotificationPayload(
            title="Alerta",
            message="Temperatura alta",
            channel=NotificationChannel.TELEGRAM,
        )
        res = await send_telegram(cfg, payload)
        self.assertTrue(res.success)
        self.assertEqual(res.channel, "telegram")
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        self.assertIn("Temperatura alta", call_kwargs["json"]["text"])

    @patch("httpx.AsyncClient.post")
    async def test_telegram_channel_api_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.headers = {"content-type": "application/json"}
        mock_resp.json.return_value = {"ok": False, "description": "Chat not found"}
        mock_post.return_value = mock_resp

        cfg = {"bot_token": "12345:ABCDEF", "chat_id": "invalid_chat"}
        payload = NotificationPayload(message="test", channel=NotificationChannel.TELEGRAM)
        res = await send_telegram(cfg, payload)
        self.assertFalse(res.success)
        self.assertIn("Chat not found", res.error)

    @patch("services.notifications.channels.telegram.httpx.AsyncClient.post")
    async def test_telegram_channel_env_interpolation(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-type": "application/json"}
        mock_resp.json.return_value = {"ok": True, "result": {"message_id": 101}}
        mock_post.return_value = mock_resp

        import os
        os.environ["TEST_TG_TOKEN"] = "111222:AAA-BBB"
        os.environ["TEST_TG_CHAT"] = "998877"

        cfg = {
            "bot_token": "${TEST_TG_TOKEN}",
            "chat_id": "${TEST_TG_CHAT}",
        }
        payload = NotificationPayload(title="Test", message="Msg", channel=NotificationChannel.TELEGRAM)
        res = await send_telegram(cfg, payload)
        self.assertTrue(res.success)
        mock_post.assert_called_once()
        self.assertIn("111222:AAA-BBB", mock_post.call_args[0][0])
        self.assertEqual(mock_post.call_args[1]["json"]["chat_id"], "998877")

    @patch("services.notifications.channels.email._send_email_sync")
    async def test_email_channel_env_interpolation(self, mock_send_sync):
        import os
        os.environ["TEST_SMTP_HOST"] = "smtp.custom.org"
        os.environ["TEST_SMTP_PORT"] = "465"
        os.environ["TEST_SMTP_USER"] = "myuser@custom.org"
        os.environ["TEST_SMTP_PASS"] = "mypass123"

        cfg = {
            "smtp_host": "${TEST_SMTP_HOST}",
            "smtp_port": "${TEST_SMTP_PORT:-587}",
            "username": "${TEST_SMTP_USER}",
            "password": "${TEST_SMTP_PASS}",
            "to_addresses": ["target@example.com"],
        }
        payload = NotificationPayload(title="Test", message="Msg", channel=NotificationChannel.EMAIL)
        res = await send_email(cfg, payload)
        self.assertTrue(res.success)
        mock_send_sync.assert_called_once()
        kwargs = mock_send_sync.call_args[1]
        self.assertEqual(kwargs["smtp_host"], "smtp.custom.org")
        self.assertEqual(kwargs["smtp_port"], 465)
        self.assertEqual(kwargs["username"], "myuser@custom.org")
        self.assertEqual(kwargs["password"], "mypass123")

    @patch("httpx.AsyncClient.post")
    async def test_webhook_channel_template_rendering(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        cfg = {
            "name": "HomeAssistant",
            "url": "https://ha.example.com/api/webhook/test",
            "method": "POST",
            "headers": {"Authorization": "Bearer secret123"},
            "payload_template": '{"device": "{device}", "value": {value}, "rule": "{rule_id}"}',
        }
        payload = NotificationPayload(
            message="Alerta",
            channel=NotificationChannel.WEBHOOK,
            metadata={"device": "sensor_01", "value": 24.5, "rule_id": "temp_rule"},
        )
        res = await send_webhook(cfg, payload)
        self.assertTrue(res.success)
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        self.assertEqual(call_kwargs["headers"]["Authorization"], "Bearer secret123")
        sent_json = call_kwargs["json"]
        self.assertEqual(sent_json.get("device"), "sensor_01")
        self.assertEqual(sent_json.get("value"), 24.5)
        self.assertEqual(sent_json.get("rule"), "temp_rule")

    async def test_webhook_ssrf_protection(self):
        """Verify that webhooks targeting loopback or private ranges are blocked."""
        malicious_urls = [
            "http://127.0.0.1:8000/api/v1/devices",
            "http://localhost/admin",
            "http://192.168.1.1/router",
            "http://169.254.169.254/latest/meta-data",
            "ftp://example.com/test",
        ]
        payload = NotificationPayload(message="SSRF Test", channel=NotificationChannel.WEBHOOK)
        for url in malicious_urls:
            cfg = {"url": url, "method": "POST"}
            res = await send_webhook(cfg, payload)
            self.assertFalse(res.success)
            self.assertIn("SSRF", res.error)


class TestNotificationService(unittest.IsolatedAsyncioTestCase):

    async def test_service_dispatch_and_status(self):
        notif_cfg = {
            "email": {
                "enabled": True,
                "smtp_host": "smtp.example.com",
                "to_addresses": ["admin@example.com"],
            },
            "telegram": {
                "enabled": True,
                "bot_token": "tok123",
                "chat_id": "chat123",
            },
            "webhooks": {
                "wh1": {
                    "name": "HA",
                    "enabled": True,
                    "url": "https://ha.example.com",
                    "method": "POST",
                }
            },
        }
        service = NotificationService(notif_cfg)
        status = service.get_status()

        self.assertTrue(status["email"]["enabled"])
        self.assertTrue(status["email"]["configured"])
        self.assertTrue(status["telegram"]["enabled"])
        self.assertEqual(status["webhooks"]["total"], 1)
        self.assertEqual(status["webhooks"]["enabled_count"], 1)

    @patch("services.notifications.service.send_telegram", new_callable=AsyncMock)
    @patch("services.notifications.service.send_email", new_callable=AsyncMock)
    @patch("services.notifications.service.send_webhook", new_callable=AsyncMock)
    async def test_service_send_all(self, mock_wh, mock_email, mock_tel):
        from services.notifications.models import NotificationResult
        mock_tel.return_value = NotificationResult(success=True, channel="telegram")
        mock_email.return_value = NotificationResult(success=True, channel="email")
        mock_wh.return_value = NotificationResult(success=True, channel="webhook")

        notif_cfg = {
            "email": {"enabled": True},
            "telegram": {"enabled": True},
            "webhooks": {"wh1": {"enabled": True, "url": "https://wh.com"}},
        }
        service = NotificationService(notif_cfg)
        payload = NotificationPayload(message="All alert", channel=NotificationChannel.ALL)
        results = await service.send(payload)

        self.assertEqual(len(results), 3)
        mock_tel.assert_called_once()
        mock_email.assert_called_once()
        mock_wh.assert_called_once()


class TestRuleEngineWithNotifications(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.node_mgr = NodeManager()
        self.pin_mgr = PinManager()
        self.dev_mgr = DeviceManager(self.node_mgr, self.pin_mgr, DEVICE_REGISTRY)
        self.event_bus = EventBus()
        self.notif_service = MagicMock(spec=NotificationService)
        self.notif_service.send = AsyncMock(return_value=[])

    async def test_rule_triggers_notification_and_cooldown(self):
        rules_cfg = {
            "temp_alarm": {
                "enabled": True,
                "cooldown": 60,  # 60s cooldown
                "condition": {
                    "device": "temp_sensor",
                    "property": "value",
                    "operator": ">",
                    "value": 35,
                },
                "actions": [
                    {
                        "type": "notification",
                        "channel": "telegram",
                        "title": "Alerta Térmica: {device}",
                        "message": "Valor {value} supera {threshold}",
                    }
                ],
            }
        }
        engine = RuleEngine(
            rules_cfg,
            self.dev_mgr,
            self.event_bus,
            notification_service=self.notif_service,
        )
        engine.start()

        # Trigger 1: value = 38 > 35 -> Condition matches
        event1 = Event(
            topic="device.value_changed",
            sender="temp_sensor",
            payload={"id": "temp_sensor", "value": 38},
        )
        await engine._on_device_value_changed(event1)
        self.assertEqual(self.notif_service.send.call_count, 1)
        sent_payload = self.notif_service.send.call_args[0][0]
        self.assertEqual(sent_payload.title, "Alerta Térmica: temp_sensor")
        self.assertEqual(sent_payload.message, "Valor 38 supera 35")

        # Trigger 2 with retrigger while in cooldown: should NOT send notification again
        rules_cfg["temp_alarm"]["retrigger"] = True
        event2 = Event(
            topic="device.value_changed",
            sender="temp_sensor",
            payload={"id": "temp_sensor", "value": 40},
        )
        await engine._on_device_value_changed(event2)
        # Call count should remain 1 due to cooldown
        self.assertEqual(self.notif_service.send.call_count, 1)

        engine.stop()

    async def test_rule_recovery_notification(self):
        rules_cfg = {
            "moisture_alarm": {
                "enabled": True,
                "recovery_message": "Humedad normalizada en {device}: {value}%",
                "condition": {
                    "device": "soil_01",
                    "property": "value",
                    "operator": "<",
                    "value": 20,
                },
                "actions": [
                    {
                        "type": "notification",
                        "channel": "email",
                        "message": "Suelo seco: {value}%",
                    }
                ],
            }
        }
        engine = RuleEngine(
            rules_cfg,
            self.dev_mgr,
            self.event_bus,
            notification_service=self.notif_service,
        )
        engine.start()

        # 1. Trigger alarm: value = 15 (< 20)
        await engine._on_device_value_changed(
            Event(topic="device.value_changed", sender="soil_01", payload={"id": "soil_01", "value": 15})
        )
        self.assertEqual(self.notif_service.send.call_count, 1)

        # 2. Condition resets: value = 45 (not < 20)
        await engine._on_device_value_changed(
            Event(topic="device.value_changed", sender="soil_01", payload={"id": "soil_01", "value": 45})
        )
        # Recovery notification should be triggered
        self.assertEqual(self.notif_service.send.call_count, 2)
        rec_payload = self.notif_service.send.call_args[0][0]
        self.assertIn("Recuperación", rec_payload.title)
        self.assertEqual(rec_payload.message, "Humedad normalizada en soil_01: 45%")

        engine.stop()


class TestNotificationValidationAndYaml(unittest.TestCase):

    def test_validator_rejects_invalid_notifications(self):
        bad_config = {
            "system": {"name": "test"},
            "notifications": {
                "email": {
                    "enabled": True,
                    "smtp_host": "",  # missing host
                    "smtp_port": 999999,  # invalid port
                    "to_addresses": [],
                },
                "telegram": {
                    "enabled": True,
                    "bot_token": "",  # missing token
                    "chat_id": "",
                },
                "webhooks": {
                    "bad_hook": {
                        "url": "ftp://not-supported",  # invalid scheme
                        "method": "DELETE",  # unsupported method
                    }
                },
            },
        }
        res = ConfigValidator.validate_dict(bad_config)
        self.assertFalse(res.valid)
        error_fields = [e.field for e in res.errors]
        self.assertIn("notifications.email.smtp_host", error_fields)
        self.assertIn("notifications.email.smtp_port", error_fields)
        self.assertIn("notifications.telegram.bot_token", error_fields)
        self.assertIn("notifications.webhooks.bad_hook.url", error_fields)
        self.assertIn("notifications.webhooks.bad_hook.method", error_fields)

    def test_secrets_masking_and_unmasking(self):
        raw_dict = {
            "nodes": {
                "node_1": {"driver": "secure_standard_firmata_wifi", "auth_key": "node_secret_key_123"}
            },
            "notifications": {
                "email": {"password": "email_secret_password"},
                "telegram": {"bot_token": "telegram_secret_bot_token"},
                "webhooks": {
                    "h1": {
                        "url": "https://api.com",
                        "headers": {"Authorization": "Bearer secret_api_token"},
                    }
                },
            },
        }
        # Mask
        masked = mask_secrets(raw_dict)
        self.assertEqual(masked["nodes"]["node_1"]["auth_key"], MASKED_SECRET_SENTINEL)
        self.assertEqual(masked["notifications"]["email"]["password"], MASKED_SECRET_SENTINEL)
        self.assertEqual(masked["notifications"]["telegram"]["bot_token"], MASKED_SECRET_SENTINEL)
        self.assertEqual(masked["notifications"]["webhooks"]["h1"]["headers"]["Authorization"], MASKED_SECRET_SENTINEL)

        # Unmask with reference
        unmasked = unmask_secrets(masked, raw_dict)
        self.assertEqual(unmasked["nodes"]["node_1"]["auth_key"], "node_secret_key_123")
        self.assertEqual(unmasked["notifications"]["email"]["password"], "email_secret_password")
        self.assertEqual(unmasked["notifications"]["telegram"]["bot_token"], "telegram_secret_bot_token")
        self.assertEqual(unmasked["notifications"]["webhooks"]["h1"]["headers"]["Authorization"], "Bearer secret_api_token")


if __name__ == "__main__":
    unittest.main()
