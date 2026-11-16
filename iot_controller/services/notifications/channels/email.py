import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict
from services.notifications.models import NotificationPayload, NotificationResult
from utils.logging import get_logger

logger = get_logger("EmailChannel")


def _send_email_sync(
    smtp_host: str,
    smtp_port: int,
    use_tls: bool,
    username: str,
    password: str,
    from_addr: str,
    to_addrs: list,
    subject: str,
    body: str,
    timeout: float = 10.0,
) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)

    part_text = MIMEText(body, "plain", "utf-8")
    msg.attach(part_text)

    # Optional HTML formatting if simple
    html_body = f"""<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
  <div style="background-color: #059669; color: white; padding: 12px 20px; border-radius: 6px 6px 0 0;">
    <h2 style="margin: 0; font-size: 18px;">🌿 TerraNode - {subject}</h2>
  </div>
  <div style="padding: 20px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 6px 6px; background-color: #f9fafb;">
    <p style="white-space: pre-wrap; font-size: 14px;">{body}</p>
    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;" />
    <p style="font-size: 12px; color: #6b7280; margin: 0;">Enviado automáticamente por el controlador TerraNode.</p>
  </div>
</body>
</html>"""
    part_html = MIMEText(html_body, "html", "utf-8")
    msg.attach(part_html)

    if smtp_port == 465:
        # Direct SSL
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=timeout) as server:
            if username and password:
                server.login(username, password)
            server.sendmail(from_addr, to_addrs, msg.as_string())
    else:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=timeout) as server:
            server.ehlo()
            if use_tls:
                server.starttls()
                server.ehlo()
            if username and password:
                server.login(username, password)
            server.sendmail(from_addr, to_addrs, msg.as_string())


async def send_email(cfg: Dict[str, Any], payload: NotificationPayload) -> NotificationResult:
    """Async wrapper sending email via thread pool."""
    from core.config import interpolate_env_vars

    smtp_host = interpolate_env_vars(str(cfg.get("smtp_host", ""))).strip()
    raw_port = interpolate_env_vars(str(cfg.get("smtp_port", 587))).strip()
    smtp_port = int(raw_port) if raw_port.isdigit() else 587
    use_tls = bool(cfg.get("use_tls", True))
    username = interpolate_env_vars(str(cfg.get("username", ""))).strip()
    password = interpolate_env_vars(str(cfg.get("password", ""))).strip()
    raw_from = interpolate_env_vars(str(cfg.get("from_address", ""))).strip()
    from_addr = raw_from or username
    to_addrs = cfg.get("to_addresses", [])

    if isinstance(to_addrs, str):
        to_addrs = [interpolate_env_vars(a.strip()) for a in to_addrs.split(",") if a.strip()]
    elif isinstance(to_addrs, list):
        to_addrs = [interpolate_env_vars(str(a).strip()) for a in to_addrs if str(a).strip()]

    if not smtp_host:
        return NotificationResult(
            success=False,
            channel="email",
            error="Servidor SMTP no configurado (smtp_host vacío).",
        )

    if not to_addrs:
        return NotificationResult(
            success=False,
            channel="email",
            error="Lista de destinatarios de correo vacía (to_addresses).",
        )

    subject = payload.title or "Notificación de TerraNode"
    body = payload.message

    try:
        await asyncio.to_thread(
            _send_email_sync,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            use_tls=use_tls,
            username=username,
            password=password,
            from_addr=from_addr,
            to_addrs=to_addrs,
            subject=subject,
            body=body,
        )
        logger.info(f"Email successfully sent to {to_addrs} via {smtp_host}:{smtp_port}")
        return NotificationResult(
            success=True,
            channel="email",
            target=", ".join(to_addrs),
            message=f"Correo enviado exitosamente a {len(to_addrs)} destinatario(s).",
        )
    except smtplib.SMTPAuthenticationError as e:
        err = f"Fallo de autenticación SMTP: {e.smtp_error.decode('utf-8', errors='ignore') if isinstance(e.smtp_error, bytes) else e}"
        logger.error(f"Email auth failed: {err}")
        return NotificationResult(success=False, channel="email", error=err)
    except Exception as e:
        logger.error(f"Failed to send email to {to_addrs}: {e}")
        return NotificationResult(success=False, channel="email", error=str(e))
