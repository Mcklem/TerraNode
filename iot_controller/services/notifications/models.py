from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class NotificationChannel(str, Enum):
    EMAIL = "email"
    TELEGRAM = "telegram"
    WEBHOOK = "webhook"
    ALL = "all"


class NotificationPayload(BaseModel):
    """Payload to be dispatched via notification channels."""
    title: Optional[str] = Field(default=None, description="Title or subject of the notification")
    message: str = Field(..., description="Main notification message text")
    channel: NotificationChannel = Field(
        default=NotificationChannel.ALL,
        description="Target notification channel",
    )
    webhook_id: Optional[str] = Field(
        default=None,
        description="Specific webhook identifier to trigger when channel is webhook or all",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary contextual metadata (device, rule, sensor values)",
    )


class NotificationResult(BaseModel):
    """Result of an individual channel dispatch or test."""
    success: bool
    channel: str
    target: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


class EmailConfig(BaseModel):
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    use_tls: bool = True
    username: str = ""
    password: str = ""
    from_address: str = ""
    to_addresses: List[str] = Field(default_factory=list)


class TelegramConfig(BaseModel):
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""


class WebhookConfig(BaseModel):
    name: Optional[str] = None
    enabled: bool = True
    url: str = ""
    method: str = "POST"
    headers: Dict[str, str] = Field(default_factory=dict)
    payload_template: Optional[str] = None


class NotificationsConfig(BaseModel):
    email: EmailConfig = Field(default_factory=EmailConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    webhooks: Dict[str, WebhookConfig] = Field(default_factory=dict)
