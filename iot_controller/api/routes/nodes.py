from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from api.dependencies import get_node_manager, get_live_command_service, get_pin_manager
from core.node_manager import NodeManager
from core.pin_manager import PinManager
from services.live_command import LiveCommandService

router = APIRouter(prefix="/api/v1/nodes", tags=["Nodes"])


class RawPinCommand(BaseModel):
    command_type: str = Field(
        ...,
        description="Tipo de operación de bajo nivel: 'digital_write' o 'analog_write' (PWM).",
        examples=["digital_write", "analog_write"]
    )
    pin: str = Field(
        ...,
        description="Identificador del pin en el nodo (ej. 'D5', 'D1', 'A0').",
        examples=["D5", "D1", "A0"]
    )
    value: int = Field(
        ...,
        description="Valor a escribir en el pin: 0 o 1 para digital; 0-255 para analógico/PWM.",
        examples=[1, 0, 128]
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "summary": "Escritura Digital HIGH en Pin D5",
                    "value": {
                        "command_type": "digital_write",
                        "pin": "D5",
                        "value": 1
                    }
                },
                {
                    "summary": "Escritura Analógica PWM (50% ciclo útil)",
                    "value": {
                        "command_type": "analog_write",
                        "pin": "D1",
                        "value": 128
                    }
                }
            ]
        }
    )


class NodeInfoResponse(BaseModel):
    id: str = Field(..., description="ID único del nodo hardware")
    connected: bool = Field(..., description="Estado actual de la conexión de red/firmata")
    driver: str = Field(..., description="Tipo de driver de nodo ('firmata', 'mock', etc.)")
    host: str = Field(..., description="Dirección IP o puerto serie de conexión")
    port: int = Field(..., description="Puerto TCP de comunicación")
    enabled: bool = Field(..., description="Indica si el nodo está habilitado en la configuración")
    status: str = Field(..., description="Estado operativo ('CONNECTED', 'DISCONNECTED', 'RECONNECTING', 'ERROR')")
    last_error: Optional[str] = Field(None, description="Último mensaje de error de conexión o seguridad registrado")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "node_jardin",
                "connected": True,
                "driver": "mock",
                "host": "192.168.1.150",
                "port": 3030,
                "enabled": True,
                "status": "CONNECTED",
                "last_error": None
            }
        }
    )


@router.get(
    "",
    response_model=List[NodeInfoResponse],
    summary="Listar nodos hardware registrados",
    description="Retorna el listado y estado de conexión de todos los nodos hardware/mock gestionados por el `NodeManager`.",
)
async def list_nodes(node_mgr: NodeManager = Depends(get_node_manager)):
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
            "last_error": getattr(node, "_last_error", None),
        })
    return result


@router.get(
    "/{node_id}",
    response_model=NodeInfoResponse,
    summary="Consultar detalle de un nodo específico",
    description="Retorna el estado de conexión e información de red de un nodo por su ID.",
    responses={
        404: {"description": "Nodo no encontrado."}
    }
)
async def get_node_details(node_id: str, node_mgr: NodeManager = Depends(get_node_manager)):
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
        "last_error": getattr(node, "_last_error", None),
    }


@router.post(
    "/{node_id}/pin",
    response_model=Dict[str, Any],
    summary="Ejecutar comando crudo sobre un pin físico del nodo",
    description="Permite enviar órdenes directas de bajo nivel (`digital_write`, `analog_write`) a un pin específico de un nodo hardware, omitiendo la capa de abstracción de dispositivos.",
    responses={
        400: {"description": "Nodo desconectado o tipo de comando inválido."},
        500: {"description": "Fallo en la comunicación con el microcontrolador."}
    }
)
async def execute_raw_pin_command(
    node_id: str,
    body: RawPinCommand,
    live_service: LiveCommandService = Depends(get_live_command_service),
    pin_mgr: Optional[PinManager] = Depends(get_pin_manager),
):
    if pin_mgr:
        allocated_dev = pin_mgr.get_allocated_device(node_id, body.pin)
        if allocated_dev:
            raise HTTPException(
                status_code=400,
                detail=f"Pin '{body.pin}' on node '{node_id}' is reserved by active device '{allocated_dev}'",
            )
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

