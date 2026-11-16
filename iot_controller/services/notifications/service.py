from typing import Any, Dict, List, Optional
from config_manager.yaml_parser import is_secret_masked
from services.notifications.channels.email import send_email
from services.notifications.channels.telegram import send_telegram
from services.notifications.channels.webhook import send_webhook
from services.notifications.models import (
    NotificationChannel,
    NotificationPayload,
    NotificationResult,
)
from utils.logging import get_logger

logger = get_logger("NotificationService")


class NotificationService:
    """Orchestrates multi-channel notification dispatching and diagnostic testing."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config: Dict[str, Any] = config or {}

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """Update notification configuration dynamically."""
        self.config = new_config or {}
        logger.info("NotificationService configuration updated.")

    def get_status(self) -> Dict[str, Any]:
        """Return operational status and summary of configured channels."""
        cfg = self.config if "notifications" not in self.config else self.config.get("notifications", {})

        email_cfg = cfg.get("email", {})
        telegram_cfg = cfg.get("telegram", {})
        webhooks_cfg = cfg.get("webhooks", {})

        webhooks_list = []
        if isinstance(webhooks_cfg, dict):
            for w_id, w_data in webhooks_cfg.items():
                if isinstance(w_data, dict):
                    webhooks_list.append({
                        "id": w_id,
                        "name": w_data.get("name") or w_id,
                        "url": w_data.get("url", ""),
                        "method": w_data.get("method", "POST"),
                        "enabled": bool(w_data.get("enabled", True)),
                    })

        return {
            "email": {
                "enabled": bool(email_cfg.get("enabled", False)),
                "configured": bool(email_cfg.get("smtp_host") and email_cfg.get("to_addresses")),
                "smtp_host": email_cfg.get("smtp_host", ""),
                "to_addresses_count": len(email_cfg.get("to_addresses", []))
                if isinstance(email_cfg.get("to_addresses"), list)
                else 1 if email_cfg.get("to_addresses") else 0,
            },
            "telegram": {
                "enabled": bool(telegram_cfg.get("enabled", False)),
                "configured": bool(telegram_cfg.get("bot_token") and telegram_cfg.get("chat_id")),
                "chat_id": telegram_cfg.get("chat_id", ""),
            },
            "webhooks": {
                "total": len(webhooks_list),
                "enabled_count": sum(1 for w in webhooks_list if w["enabled"]),
                "items": webhooks_list,
            },
        }

    async def send(
        self,
        payload: NotificationPayload,
        template_context: Optional[Dict[str, Any]] = None,
    ) -> List[NotificationResult]:
        """Dispatch a notification payload to target channel(s)."""
        cfg = self.config if "notifications" not in self.config else self.config.get("notifications", {})
        results: List[NotificationResult] = []

        target_ch = payload.channel

        # 1. Telegram
        if target_ch in (NotificationChannel.TELEGRAM, NotificationChannel.ALL):
            tel_cfg = cfg.get("telegram", {})
            if tel_cfg.get("enabled", False) or target_ch == NotificationChannel.TELEGRAM:
                res = await send_telegram(tel_cfg, payload)
                results.append(res)

        # 2. Email
        if target_ch in (NotificationChannel.EMAIL, NotificationChannel.ALL):
            email_cfg = cfg.get("email", {})
            if email_cfg.get("enabled", False) or target_ch == NotificationChannel.EMAIL:
                res = await send_email(email_cfg, payload)
                results.append(res)

        # 3. Webhooks
        if target_ch in (NotificationChannel.WEBHOOK, NotificationChannel.ALL):
            webhooks_dict = cfg.get("webhooks", {})
            if isinstance(webhooks_dict, dict):
                if payload.webhook_id and payload.webhook_id in webhooks_dict:
                    w_cfg = webhooks_dict[payload.webhook_id]
                    if w_cfg.get("enabled", True) or target_ch == NotificationChannel.WEBHOOK:
                        res = await send_webhook(w_cfg, payload, template_context)
                        results.append(res)
                else:
                    for w_id, w_cfg in webhooks_dict.items():
                        if not isinstance(w_cfg, dict):
                            continue
                        if w_cfg.get("enabled", True):
                            res = await send_webhook(w_cfg, payload, template_context)
                            results.append(res)

        return results

    async def test_channel(
        self,
        channel: str,
        test_config: Optional[Dict[str, Any]] = None,
        webhook_id: Optional[str] = None,
        custom_message: Optional[str] = None,
    ) -> NotificationResult:
        """Execute a live diagnostic ping to verify credentials and connectivity."""
        cfg = self.config if "notifications" not in self.config else self.config.get("notifications", {})
        test_payload = NotificationPayload(
            title="🔔 Prueba de Notificación TerraNode",
            message=custom_message or "Este es un mensaje de prueba para verificar la conectividad de TerraNode.",
            channel=NotificationChannel(channel) if channel in [c.value for c in NotificationChannel] else NotificationChannel.ALL,
        )

        if channel == "telegram":
            active_cfg = dict(cfg.get("telegram", {}))
            if test_config:
                for k, v in test_config.items():
                    if k == "bot_token":
                        if v and not is_secret_masked(v):
                            active_cfg["bot_token"] = v
                    elif v is not None and str(v).strip() != "":
                        active_cfg[k] = v
            return await send_telegram(active_cfg, test_payload)

        elif channel == "email":
            active_cfg = dict(cfg.get("email", {}))
            if test_config:
                for k, v in test_config.items():
                    if k == "password":
                        if v and not is_secret_masked(v):
                            active_cfg["password"] = v
                    elif v is not None and (not isinstance(v, str) or v.strip() != ""):
                        active_cfg[k] = v
            return await send_email(active_cfg, test_payload)

        elif channel == "webhook":
            active_cfg: Dict[str, Any] = {}
            if webhook_id and isinstance(cfg.get("webhooks"), dict):
                active_cfg = dict(cfg["webhooks"].get(webhook_id, {}))
            if test_config:
                for k, v in test_config.items():
                    if k == "headers" and isinstance(v, dict):
                        active_headers = dict(active_cfg.get("headers", {}))
                        for hk, hv in v.items():
                            if hv and not is_secret_masked(hv):
                                active_headers[hk] = hv
                        active_cfg["headers"] = active_headers
                    elif v is not None:
                        active_cfg[k] = v
            return await send_webhook(active_cfg, test_payload, template_context={"test": True})

        return NotificationResult(
            success=False,
            channel=channel,
            error=f"Canal no soportado para prueba: '{channel}'.",
        )
