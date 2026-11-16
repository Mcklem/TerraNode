from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict
from api.dependencies import get_health_monitor, get_node_manager, get_device_manager
from core.node_manager import NodeManager
from core.device_manager import DeviceManager
from devices.base_device import DeviceStatus
from monitoring.health import HealthMonitor

router = APIRouter(prefix="/api/v1/health", tags=["Health"])


class HealthSummaryResponse(BaseModel):
    status: str = Field(..., description="Estado general del controlador ('OK', 'WARNING', 'ERROR')")
    total_nodes: int = Field(..., description="Número total de nodos configurados")
    connected_nodes: int = Field(..., description="Número de nodos con conexión activa")
    total_devices: int = Field(..., description="Número total de dispositivos registrados")
    report: Dict[str, Any] = Field(..., description="Reporte de salud desglosado por componente")
    message: Optional[str] = Field(None, description="Mensaje descriptivo del estado general")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "OK",
                "total_nodes": 2,
                "connected_nodes": 2,
                "total_devices": 5,
                "report": {
                    "nodes": {"n1": {"connected": True, "status": "CONNECTED"}},
                    "devices": {"pump_01": {"type": "relay", "node": "n1", "status": "OK"}}
                },
                "message": "Todos los servicios y nodos respondiendo con normalidad."
            }
        }
    )


@router.get(
    "",
    response_model=HealthSummaryResponse,
    summary="Consultar resumen de salud del controlador",
    description="Retorna un diagnóstico rápido del estado del sistema, incluyendo nodos conectados y total de dispositivos activos.",
)
async def get_health_summary(
    health_monitor: Optional[HealthMonitor] = Depends(get_health_monitor),
    node_mgr: NodeManager = Depends(get_node_manager),
    dev_mgr: DeviceManager = Depends(get_device_manager),
):
    nodes = node_mgr.get_all_nodes()
    devices = dev_mgr.get_all_devices()
    total_nodes = len(nodes)
    connected_nodes = sum(1 for n in nodes if n.is_connected())

    devices_in_error = [d.id for d in devices if d.status == DeviceStatus.ERROR]

    if total_nodes == 0:
        status = "OK"
        message = "Sin nodos configurados. Sistema en espera."
    elif connected_nodes == total_nodes:
        if devices_in_error:
            status = "WARNING"
            message = f"Todos los nodos conectados, pero {len(devices_in_error)} dispositivo(s) presentan errores."
        else:
            status = "OK"
            message = "Todos los servicios y nodos respondiendo con normalidad."
    elif connected_nodes > 0:
        status = "WARNING"
        disconnected_count = total_nodes - connected_nodes
        message = f"Operación degradada: {disconnected_count} de {total_nodes} nodo(s) desconectado(s)."
    else:
        status = "ERROR"
        message = f"Sin comunicación hardware: 0 de {total_nodes} nodos conectados."

    if health_monitor:
        status_report = health_monitor.get_system_health()
    else:
        status_report = {
            "status": status,
            "nodes_connected": f"{connected_nodes}/{total_nodes}",
            "devices_count": len(devices),
        }

    return {
        "status": status,
        "total_nodes": total_nodes,
        "connected_nodes": connected_nodes,
        "total_devices": len(devices),
        "report": status_report,
        "message": message,
    }


@router.get(
    "/system",
    response_model=Dict[str, Any],
    summary="Diagnóstico detallado de salud de nodos y dispositivos",
    description="Retorna el reporte de salud desglosado de cada nodo hardware y dispositivo en ejecución.",
    responses={
        503: {"description": "El monitor de salud (HealthMonitor) no está activo."}
    }
)
async def get_detailed_system_health(
    health_monitor: Optional[HealthMonitor] = Depends(get_health_monitor),
):
    if not health_monitor:
        raise HTTPException(status_code=503, detail="HealthMonitor is not active")
    return health_monitor.get_system_health()
