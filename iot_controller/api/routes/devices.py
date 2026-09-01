from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from api.dependencies import (
    get_device_manager,
    get_live_command_service,
    get_override_registry,
)
from core.device_manager import DeviceManager
from services.live_command import LiveCommandService, OverrideRegistry, ControlMode

router = APIRouter(prefix="/api/v1/devices", tags=["Devices"])


class CommandPayload(BaseModel):
    action: str = Field(..., description="Action name e.g. 'turn_on', 'turn_off', 'set_position'")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Arguments for the command method")
    target_mode: Optional[ControlMode] = Field(None, description="Explicit control mode lock override")
    user_id: Optional[str] = Field("REST_API_USER", description="Identifier of the requester")
    ttl_seconds: Optional[float] = Field(None, description="Optional override expiration timeout in seconds")


@router.get("", response_model=List[Dict[str, Any]])
async def list_devices(
    dev_mgr: DeviceManager = Depends(get_device_manager),
    override_reg: OverrideRegistry = Depends(get_override_registry),
):
    """List all registered sensors and actuators with state and control modes."""
    devices = dev_mgr.get_all_devices()
    result = []
    for dev in devices:
        st = override_reg.get_state(dev.id)
        dev_info = {
            "id": dev.id,
            "type": dev.type,
            "node_id": dev.node.id,
            "status": dev.status.value,
            "control_mode": st.mode.value,
            "override_active": st.is_override_active(),
            "current_state": dev.get_state(),
        }
        result.append(dev_info)
    return result


@router.get("/{device_id}", response_model=Dict[str, Any])
async def get_device(
    device_id: str,
    dev_mgr: DeviceManager = Depends(get_device_manager),
    override_reg: OverrideRegistry = Depends(get_override_registry),
):
    """Get state and readings for a specific device."""
    dev = dev_mgr.get_device(device_id)
    if not dev:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")
    st = override_reg.get_state(device_id)
    return {
        "id": dev.id,
        "type": dev.type,
        "node_id": dev.node.id,
        "status": dev.status.value,
        "control_mode": st.mode.value,
        "override_active": st.is_override_active(),
        "last_override_action": st.last_action,
        "override_source": st.override_source,
        "current_state": dev.get_state(),
    }


@router.post("/{device_id}/command", response_model=Dict[str, Any])
async def execute_device_command(
    device_id: str,
    body: CommandPayload,
    dev_mgr: DeviceManager = Depends(get_device_manager),
    live_service: LiveCommandService = Depends(get_live_command_service),
):
    """Execute a live manual command on a device and lock manual control mode."""
    dev = dev_mgr.get_device(device_id)
    if not dev:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")

    res = await live_service.execute_live_command(
        device_id=device_id,
        action=body.action,
        params=body.params,
        target_mode=body.target_mode,
        user_id=body.user_id,
        ttl_seconds=body.ttl_seconds,
    )

    if not res.success:
        raise HTTPException(status_code=400, detail=res.message)

    return {
        "success": res.success,
        "device_id": res.device_id,
        "applied_action": res.applied_action,
        "current_mode": res.current_mode.value,
        "message": res.message,
        "state_payload": res.state_payload,
    }


@router.post("/{device_id}/restore-control", response_model=Dict[str, Any])
async def restore_device_control(
    device_id: str,
    dev_mgr: DeviceManager = Depends(get_device_manager),
    live_service: LiveCommandService = Depends(get_live_command_service),
):
    """Restore device control mode back to automatic (AUTO)."""
    dev = dev_mgr.get_device(device_id)
    if not dev:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")

    res = await live_service.restore_control(device_id)
    return {
        "success": res.success,
        "device_id": res.device_id,
        "current_mode": res.current_mode.value,
        "message": res.message,
        "state_payload": res.state_payload,
    }
