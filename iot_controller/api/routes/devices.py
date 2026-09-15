from fastapi import APIRouter, Depends, HTTPException, status
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from api.dependencies import (
    get_device_manager,
    get_live_command_service,
    get_override_registry,
)
from core.device_manager import DeviceManager
from services.live_command import LiveCommandService, OverrideRegistry, ControlMode

router = APIRouter(prefix="/api/v1/devices", tags=["Devices"])


class CommandPayload(BaseModel):
    action: str = Field(
        ...,
        description="Nombre de la acción o método a ejecutar sobre el actuador (ej. 'turn_on', 'turn_off', 'set_position').",
        examples=["turn_on", "turn_off", "set_position"]
    )
    params: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Diccionario de parámetros kwargs pasados al método del actuador.",
        examples=[{}, {"angle": 90}]
    )
    target_mode: Optional[ControlMode] = Field(
        None,
        description="Modo de override manual a establecer ('MANUAL_ON', 'MANUAL_OFF', 'MANUAL_VALUE'). Si se omite, se deduce del comando.",
        examples=["MANUAL_ON", "MANUAL_OFF"]
    )
    user_id: Optional[str] = Field(
        "REST_API_OPERATOR",
        description="Identificador del operador, usuario o sistema externo que emite la orden.",
        examples=["operador_juan", "dashboard_ui"]
    )
    ttl_seconds: Optional[float] = Field(
        None,
        description="Tiempo límite de expiración (en segundos) para el modo manual. Al finalizar, vuelve automáticamente a 'AUTO'.",
        examples=[None, 300, 60]
    )

    from pydantic import model_validator

    @model_validator(mode="before")
    @classmethod
    def unwrap_value_wrapper(cls, data: Any) -> Any:
        """Unwrap payload if client or OpenAPI example sent wrapped object {'value': {...}}."""
        if isinstance(data, dict):
            if "value" in data and isinstance(data["value"], dict):
                inner = data["value"]
                if "action" in inner:
                    return inner
        return data

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "action": "turn_on",
                    "params": {},
                    "target_mode": "MANUAL_ON",
                    "user_id": "operador_sala_1",
                    "ttl_seconds": None
                },
                {
                    "action": "turn_off",
                    "params": {},
                    "target_mode": "MANUAL_OFF",
                    "user_id": "operador_sala_1"
                },
                {
                    "action": "set_position",
                    "params": {"angle": 90},
                    "user_id": "sistema_ventilacion",
                    "ttl_seconds": 300
                }
            ]
        }
    )


class DeviceStateResponse(BaseModel):
    id: str = Field(..., description="ID único del dispositivo (ej. 'pump_01', 'soil_01')")
    type: str = Field(..., description="Tipo de controlador de dispositivo (ej. 'relay', 'soil_moisture', 'servo')")
    category: str = Field(..., description="Categoría principal del dispositivo ('sensor' | 'actuator')")
    node_id: str = Field(..., description="ID del nodo hardware al que está conectado")
    status: str = Field(..., description="Estado del driver de dispositivo ('OK', 'ERROR', 'DISCONNECTED')")
    control_mode: str = Field(..., description="Modo lógico de control ('AUTO', 'MANUAL_ON', 'MANUAL_OFF', 'MANUAL_VALUE')")
    override_active: bool = Field(..., description="True si el dispositivo está bloqueado en modo manual impidiendo las reglas automáticas")
    current_state: Dict[str, Any] = Field(..., description="Payload de estado actual y lecturas/posiciones físicas del dispositivo")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "pump_01",
                "type": "relay",
                "category": "actuator",
                "node_id": "node_jardin",
                "status": "OK",
                "control_mode": "MANUAL_ON",
                "override_active": True,
                "current_state": {
                    "device_id": "pump_01",
                    "state": "ON",
                    "timestamp": 1725234500.0,
                    "status": "OK"
                }
            }
        }
    )


class CommandResultResponse(BaseModel):
    success: bool = Field(..., description="Indica si la ejecución en el hardware fue exitosa")
    device_id: str = Field(..., description="ID del dispositivo comandado")
    applied_action: str = Field(..., description="Acción ejecutada")
    current_mode: str = Field(..., description="Nuevo modo de control establecido ('MANUAL_ON', 'MANUAL_OFF', 'AUTO')")
    message: str = Field(..., description="Mensaje descriptivo del resultado o error")
    state_payload: Dict[str, Any] = Field(..., description="Estado actualizado devuelto por el driver del dispositivo")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "device_id": "pump_01",
                "applied_action": "turn_on",
                "current_mode": "MANUAL_ON",
                "message": "Successfully executed 'turn_on' on device 'pump_01'",
                "state_payload": {
                    "device_id": "pump_01",
                    "state": "ON",
                    "timestamp": 1725234510.0,
                    "status": "OK"
                }
            }
        }
    )


@router.get(
    "",
    response_model=List[DeviceStateResponse],
    summary="Listar todos los dispositivos y su estado de control",
    description="Retorna el listado completo de sensores y actuadores registrados, incluyendo su lectura/estado físico actual, estado del driver y modo de control (`AUTO`, `MANUAL_ON`, `MANUAL_OFF`).",
)
async def list_devices(
    dev_mgr: DeviceManager = Depends(get_device_manager),
    override_reg: OverrideRegistry = Depends(get_override_registry),
):
    devices = dev_mgr.get_all_devices()
    result = []
    for dev in devices:
        st = override_reg.get_state(dev.id)
        dev_info = {
            "id": dev.id,
            "type": dev.type,
            "category": dev.category,
            "node_id": dev.node.id,
            "status": dev.status.value,
            "control_mode": st.mode.value,
            "override_active": st.is_override_active(),
            "current_state": dev.get_state(),
        }
        result.append(dev_info)
    return result


@router.get(
    "/{device_id}",
    response_model=DeviceStateResponse,
    summary="Consultar detalle de un dispositivo específico",
    description="Retorna el estado de lecturas físicas, estado de salud y detalles del modo de override manual de un dispositivo por su ID.",
    responses={
        404: {"description": "Dispositivo no encontrado en la configuración activa del sistema."}
    }
)
async def get_device(
    device_id: str,
    dev_mgr: DeviceManager = Depends(get_device_manager),
    override_reg: OverrideRegistry = Depends(get_override_registry),
):
    dev = dev_mgr.get_device(device_id)
    if not dev:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")
    st = override_reg.get_state(device_id)
    return {
        "id": dev.id,
        "type": dev.type,
        "category": dev.category,
        "node_id": dev.node.id,
        "status": dev.status.value,
        "control_mode": st.mode.value,
        "override_active": st.is_override_active(),
        "current_state": dev.get_state(),
    }


@router.post(
    "/{device_id}/command",
    response_model=CommandResultResponse,
    summary="Ejecutar comando directo en vivo (Live Command) e iniciar Override",
    description="""
Envía un comando en vivo actuando directamente sobre el nodo físico del dispositivo y **fija el modo de control manual** (`MANUAL_ON`, `MANUAL_OFF`, `MANUAL_VALUE`).

### 🛡️ Garantía de Prevalencia de Control
Una vez ejecutado este comando, el motor de automatización (`RuleEngine`) **no podrá cambiar el estado del actuador** aunque se cumplan reglas automáticas, hasta que se invoque `restore-control` o venza el tiempo `ttl_seconds`.

### 💡 Ejemplos de Acciones Disponibles por Dispositivo:
- **Relés / Bombas / Solenoides:**
  - `action: "turn_on"` -> Enciende el relé y fija modo `MANUAL_ON`.
  - `action: "turn_off"` -> Apaga el relé y fija modo `MANUAL_OFF`.
- **Servomotores:**
  - `action: "set_position"`, `params: {"angle": 45}` -> Establece el ángulo del servo y fija modo `MANUAL_VALUE`.
""",
    responses={
        400: {"description": "Error en los parámetros o fallo en la ejecución del hardware."},
        404: {"description": "El dispositivo especificado no existe."}
    }
)
async def execute_device_command(
    device_id: str,
    body: CommandPayload,
    dev_mgr: DeviceManager = Depends(get_device_manager),
    live_service: LiveCommandService = Depends(get_live_command_service),
):
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


@router.post(
    "/{device_id}/restore-control",
    response_model=CommandResultResponse,
    summary="Restablecer control automático (AUTO)",
    description="Elimina el bloqueo de override manual y devuelve la gestión del dispositivo al modo automático (`AUTO`), permitiendo que el motor de reglas (`RuleEngine`) vuelva a tomar el control.",
    responses={
        404: {"description": "Dispositivo no encontrado."}
    }
)
async def restore_device_control(
    device_id: str,
    dev_mgr: DeviceManager = Depends(get_device_manager),
    live_service: LiveCommandService = Depends(get_live_command_service),
):
    dev = dev_mgr.get_device(device_id)
    if not dev:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")

    res = await live_service.restore_control(device_id)
    return {
        "success": res.success,
        "device_id": res.device_id,
        "applied_action": res.applied_action,
        "current_mode": res.current_mode.value,
        "message": res.message,
        "state_payload": res.state_payload,
    }
