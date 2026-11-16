from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from api.dependencies import get_notification_service
from services.notifications import NotificationResult, NotificationService

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])


class TestNotificationRequest(BaseModel):
    channel: str = Field(..., description="Target channel: 'email', 'telegram', or 'webhook'")
    webhook_id: Optional[str] = Field(default=None, description="Specific webhook ID when testing webhook")
    config_override: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional channel credentials to test before committing changes",
    )
    message: Optional[str] = Field(
        default=None,
        description="Optional custom test message text",
    )


@router.get("/status")
async def get_notification_status(
    service: NotificationService = Depends(get_notification_service),
):
    """Retrieve operational status and configured channels summary."""
    return service.get_status()


@router.post("/test", response_model=NotificationResult)
async def test_notification(
    req: TestNotificationRequest,
    service: NotificationService = Depends(get_notification_service),
):
    """
    Execute a live diagnostic ping to verify credentials and connectivity for Email, Telegram, or Webhooks.
    """
    if req.channel not in ("email", "telegram", "webhook"):
        raise HTTPException(
            status_code=400,
            detail=f"Canal inválido '{req.channel}'. Los canales soportados son: 'email', 'telegram', 'webhook'.",
        )

    result = await service.test_channel(
        channel=req.channel,
        test_config=req.config_override,
        webhook_id=req.webhook_id,
        custom_message=req.message,
    )
    return result
