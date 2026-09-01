from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from api.dependencies import get_node_manager, get_live_command_service
from core.node_manager import NodeManager
from services.live_command import LiveCommandService

router = APIRouter(prefix="/api/v1/nodes", tags=["Nodes"])


class RawPinCommand(BaseModel):
    command_type: str = Field(..., description="'digital_write' or 'analog_write'")
    pin: str = Field(..., description="Pin identifier e.g. 'D5', 'A0'")
    value: int = Field(..., description="Pin output value e.g. 0, 1, or PWM (0-255)")


@router.get("", response_model=List[Dict[str, Any]])
async def list_nodes(node_mgr: NodeManager = Depends(get_node_manager)):
    """List all hardware nodes registered in the system."""
    result = []
    for node in node_mgr.get_all_nodes():
        result.append({
            "id": node.id,
            "connected": node.is_connected(),
            "driver": node.driver,
            "host": node.host,
            "port": node.port,
            "enabled": node.enabled,
            "status": node.status.value,
        })
    return result


@router.get("/{node_id}", response_model=Dict[str, Any])
async def get_node_details(node_id: str, node_mgr: NodeManager = Depends(get_node_manager)):
    """Get details for a specific hardware node."""
    node = node_mgr.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")
    return {
        "id": node.id,
        "connected": node.is_connected(),
        "driver": node.driver,
        "host": node.host,
        "port": node.port,
        "enabled": node.enabled,
        "status": node.status.value,
    }


@router.post("/{node_id}/pin", response_model=Dict[str, Any])
async def execute_raw_pin_command(
    node_id: str,
    body: RawPinCommand,
    live_service: LiveCommandService = Depends(get_live_command_service),
):
    """Execute raw digital/analog write on a specific node pin."""
    try:
        res = await live_service.execute_raw_node_command(
            node_id=node_id,
            command_type=body.command_type,
            pin=body.pin,
            value=body.value,
        )
        return {"status": "success", "data": res}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed raw pin execution: {e}")
