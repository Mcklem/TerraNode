import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from api.app import create_app
from services.notifications.models import NotificationResult


class TestApiNotifications(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_get_notification_status(self):
        resp = self.client.get("/api/v1/notifications/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("email", data)
        self.assertIn("telegram", data)
        self.assertIn("webhooks", data)
        self.assertIn("enabled", data["email"])
        self.assertIn("enabled", data["telegram"])
        self.assertIn("total", data["webhooks"])

    @patch("services.notifications.service.send_telegram", new_callable=AsyncMock)
    def test_post_test_notification_telegram(self, mock_send_telegram):
        mock_send_telegram.return_value = NotificationResult(
            success=True,
            channel="telegram",
            target="123456",
            message="Test OK",
        )

        payload = {
            "channel": "telegram",
            "config_override": {
                "bot_token": "test_token",
                "chat_id": "123456",
            },
            "message": "Custom test message",
        }
        resp = self.client.post("/api/v1/notifications/test", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["channel"], "telegram")
        mock_send_telegram.assert_called_once()

    def test_post_test_notification_invalid_channel(self):
        resp = self.client.post(
            "/api/v1/notifications/test",
            json={"channel": "unsupported_channel"},
        )
        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()
