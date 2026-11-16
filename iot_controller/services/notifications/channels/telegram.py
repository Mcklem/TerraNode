from typing import Any, Dict
import httpx
from services.notifications.models import NotificationPayload, NotificationResult
from utils.logging import get_logger

logger = get_logger("TelegramChannel")


async def send_telegram(cfg: Dict[str, Any], payload: NotificationPayload) -> NotificationResult:
    """Send notification message via Telegram Bot HTTP API."""
    from core.config import interpolate_env_vars

    raw_token = str(cfg.get("bot_token", "")).strip()
    raw_chat = str(cfg.get("chat_id", "")).strip()
    bot_token = interpolate_env_vars(raw_token).strip()
    chat_id = interpolate_env_vars(raw_chat).strip()

    if not bot_token:
        return NotificationResult(
            success=False,
            channel="telegram",
            error="Token de Telegram Bot no configurado (bot_token vacío).",
        )

    if not chat_id:
        return NotificationResult(
            success=False,
            channel="telegram",
            error="Identificador de chat de Telegram no configurado (chat_id vacío).",
        )

    # Format text
    text_content = ""
    if payload.title:
        text_content += f"*{payload.title}*\n\n"
    text_content += payload.message

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    body = {
        "chat_id": chat_id,
        "text": text_content,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=body)
            data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}

            if resp.status_code == 200 and data.get("ok"):
                logger.info(f"Telegram message successfully delivered to chat_id={chat_id}")
                return NotificationResult(
                    success=True,
                    channel="telegram",
                    target=chat_id,
                    message="Mensaje de Telegram enviado con éxito.",
                )
            else:
                desc = data.get("description", resp.text)
                if "chat not found" in desc.lower():
                    err = (
                        f"Error en Telegram Bot API (Chat not found para {chat_id}): En Telegram los bots no pueden iniciar conversaciones. "
                        f"Debes abrir el bot en Telegram y pulsar 'Iniciar' o enviarle '/start' para autorizar el envío de mensajes."
                    )
                elif "unauthorized" in desc.lower():
                    err = f"Token de bot no autorizado (HTTP 401). Verifica que el 'bot_token' sea correcto."
                else:
                    err = f"Error en Telegram Bot API (HTTP {resp.status_code}): {desc}"
                logger.error(err)
                return NotificationResult(success=False, channel="telegram", error=err)
    except httpx.TimeoutException:
        err = "Tiempo de espera agotado al conectar con api.telegram.org."
        logger.error(err)
        return NotificationResult(success=False, channel="telegram", error=err)
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")
        return NotificationResult(success=False, channel="telegram", error=str(e))
