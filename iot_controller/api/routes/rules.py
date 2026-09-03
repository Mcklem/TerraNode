from fastapi import APIRouter, Depends, HTTPException, status
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from api.dependencies import get_rule_engine

router = APIRouter(prefix="/api/v1/rules", tags=["Rules"])


class RuleConditionResponse(BaseModel):
    device: str = Field(..., description="ID del sensor evaluado (ej. 'light_01')")
    property: str = Field("value", description="Propiedad evaluada ('value', 'temperature', 'pressure', etc.)")
    operator: str = Field(..., description="Operador de comparación ('<', '>', '==', '!=', etc.)")
    value: Any = Field(..., description="Valor umbral de disparo")


class RuleActionResponse(BaseModel):
    device: str = Field(..., description="ID del actuador objetivo (ej. 'irrigation_pump')")
    command: str = Field(..., description="Comando a ejecutar (ej. 'turn_on', 'set_position')")
    args: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Parámetros adicionales del comando")


class RuleStateResponse(BaseModel):
    id: str = Field(..., description="ID de la regla de automatización (ej. 'irrigation_start')")
    enabled: bool = Field(True, description="Indica si la regla está activa")
    condition: RuleConditionResponse = Field(..., description="Condición del sensor para evaluar el disparo")
    actions: List[RuleActionResponse] = Field(default_factory=list, description="Lista de acciones a ejecutar")
    retrigger: bool = Field(False, description="True si la regla se dispara repetidamente en cada medición activa")
    is_triggered: bool = Field(False, description="True si la condición de la regla se encuentra actualmente cumplida")
    last_sensor_value: Optional[Any] = Field(None, description="Última lectura registrada del sensor de la condición")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "irrigation_start",
                "enabled": True,
                "condition": {
                    "device": "light_01",
                    "property": "value",
                    "operator": "<",
                    "value": 400
                },
                "actions": [
                    {
                        "device": "irrigation_pump",
                        "command": "turn_on",
                        "args": {}
                    }
                ],
                "retrigger": False,
                "is_triggered": True,
                "last_sensor_value": 312
            }
        }
    )


@router.get(
    "",
    response_model=List[RuleStateResponse],
    summary="Listar reglas de automatización por sensores",
    description="Retorna el listado completo de reglas declarativas de automatización por umbrales de sensores configuradas en `RuleEngine`, mostrando su condición, acciones, valor actual del sensor y estado de disparo.",
)
async def list_rules(rule_engine: Any = Depends(get_rule_engine)):
    return rule_engine.get_rule_states()


@router.get(
    "/{rule_id}",
    response_model=RuleStateResponse,
    summary="Obtener detalles de una regla específica",
    description="Retorna la información completa de configuración y estado en tiempo real de una regla de automatización por su ID.",
    responses={
        404: {"description": "Regla no encontrada en la configuración activa."}
    }
)
async def get_rule_detail(
    rule_id: str,
    rule_engine: Any = Depends(get_rule_engine),
):
    states = rule_engine.get_rule_states()
    for rule in states:
        if rule["id"] == rule_id:
            return rule
    raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found in active settings")


@router.post(
    "/{rule_id}/toggle",
    response_model=Dict[str, Any],
    summary="Habilitar o pausar una regla de automatización",
    description="Permite activar o desactivar dinámicamente el procesamiento de una regla sin reiniciar el sistema.",
    responses={
        404: {"description": "Regla no encontrada."}
    }
)
async def toggle_rule(
    rule_id: str,
    rule_engine: Any = Depends(get_rule_engine),
):
    new_state = rule_engine.toggle_rule(rule_id)
    if new_state is None:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")

    return {
        "rule_id": rule_id,
        "enabled": new_state,
        "message": f"Rule '{rule_id}' is now {'enabled' if new_state else 'disabled'}",
    }
