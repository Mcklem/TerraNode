import json
from datetime import datetime
from typing import Any, Dict, Optional
import httpx
from services.notifications.models import NotificationPayload, NotificationResult
from utils.logging import get_logger

logger = get_logger("WebhookChannel")


def _render_template(template_str: str, context: Dict[str, Any]) -> str:
    """Safely format string replacing {keys} present in context."""
    res = template_str
    for k, v in context.items():
        placeholder = "{" + str(k) + "}"
        if placeholder in res:
            res = res.replace(placeholder, str(v))
    return res


async def send_webhook(
    cfg: Dict[str, Any],
    payload: NotificationPayload,
    template_context: Optional[Dict[str, Any]] = None,
) -> NotificationResult:
    """Send webhook HTTP request according to custom configuration."""
    from core.config import interpolate_env_vars

    raw_url = str(cfg.get("url", "")).strip()
    url = interpolate_env_vars(raw_url).strip()
    name = cfg.get("name") or "webhook"
    method = cfg.get("method", "POST").upper()
    headers = {hk: interpolate_env_vars(str(hv)) for hk, hv in dict(cfg.get("headers", {})).items()}
    payload_template = cfg.get("payload_template")

    if not url:
        return NotificationResult(
            success=False,
            channel="webhook",
            target=name,
            error=f"URL del Webhook '{name}' no configurada.",
        )

    # Build context for template substitution
    ctx = {
        "title": payload.title or "",
        "message": payload.message,
        "channel": payload.channel.value,
        "timestamp": datetime.now().isoformat(),
    }
    if payload.metadata:
        ctx.update(payload.metadata)
    if template_context:
        ctx.update(template_context)

    # Prepare request data
    data_to_send: Any = None
    headers.setdefault("Content-Type", "application/json")
    is_json = "application/json" in headers.get("Content-Type", "").lower()

    if payload_template and payload_template.strip():
        rendered_str = _render_template(payload_template, ctx)
        if is_json:
            try:
                data_to_send = json.loads(rendered_str)
            except Exception:
                # If it cannot parse as json, send as raw content
                data_to_send = rendered_str
        else:
            data_to_send = rendered_str
    else:
        # Default structured JSON payload
        data_to_send = {
            "title": payload.title,
            "message": payload.message,
            "channel": payload.channel.value,
            "timestamp": datetime.now().isoformat(),
            "metadata": payload.metadata,
        }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if method == "GET":
                resp = await client.get(url, headers=headers, params=data_to_send if isinstance(data_to_send, dict) else None)
            elif method == "PUT":
                if isinstance(data_to_send, (dict, list)):
                    resp = await client.put(url, headers=headers, json=data_to_send)
                else:
                    resp = await client.put(url, headers=headers, content=str(data_to_send))
            else:  # Default POST
                if isinstance(data_to_send, (dict, list)):
                    resp = await client.post(url, headers=headers, json=data_to_send)
                else:
                    resp = await client.post(url, headers=headers, content=str(data_to_send))

            if 200 <= resp.status_code < 300:
                logger.info(f"Webhook '{name}' [{method} {url}] executed successfully (HTTP {resp.status_code}).")
                return NotificationResult(
                    success=True,
                    channel="webhook",
                    target=f"{name} ({url})",
                    message=f"Webhook ejecutado con éxito (HTTP {resp.status_code}).",
                )
            else:
                err = f"El servidor webhook '{name}' respondió con error HTTP {resp.status_code}: {resp.text[:200]}"
                logger.warning(err)
                return NotificationResult(
                    success=False,
                    channel="webhook",
                    target=f"{name} ({url})",
                    error=err,
                )
    except httpx.TimeoutException:
        err = f"Tiempo de espera agotado al conectar con webhook '{name}' ({url})."
        logger.error(err)
        return NotificationResult(success=False, channel="webhook", target=url, error=err)
    except Exception as e:
        err = f"Fallo al ejecutar webhook '{name}': {e}"
        logger.error(err)
        return NotificationResult(success=False, channel="webhook", target=url, error=err)
