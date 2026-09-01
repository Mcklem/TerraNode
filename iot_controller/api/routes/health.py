from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, Optional
from api.dependencies import get_health_monitor, get_node_manager, get_device_manager
from core.node_manager import NodeManager
from core.device_manager import DeviceManager
from monitoring.health import HealthMonitor

router = APIRouter(prefix="/api/v1/health", tags=["Health"])


@router.get("", response_model=Dict[str, Any])
async def get_health_summary(
    health_monitor: Optional[HealthMonitor] = Depends(get_health_monitor),
    node_mgr: NodeManager = Depends(get_node_manager),
    dev_mgr: DeviceManager = Depends(get_device_manager),
):
    """Get high-level operational health status of the controller."""
    nodes = node_mgr.get_all_nodes()
    connected_nodes = sum(1 for n in nodes if n.is_connected())

    if health_monitor:
        status_report = health_monitor.get_system_health()
    else:
        status_report = {
            "status": "OK" if connected_nodes > 0 else "WARNING",
            "nodes_connected": f"{connected_nodes}/{len(nodes)}",
            "devices_count": len(dev_mgr.get_all_devices()),
        }

    return {
        "status": "OK" if connected_nodes > 0 else "WARNING",
        "total_nodes": len(nodes),
        "connected_nodes": connected_nodes,
        "total_devices": len(dev_mgr.get_all_devices()),
        "report": status_report,
    }


@router.get("/system", response_model=Dict[str, Any])
async def get_detailed_system_health(
    health_monitor: Optional[HealthMonitor] = Depends(get_health_monitor),
):
    """Get detailed health diagnostic report."""
    if not health_monitor:
        raise HTTPException(status_code=503, detail="HealthMonitor is not active")
    return health_monitor.get_system_health()
