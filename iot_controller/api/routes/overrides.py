from fastapi import APIRouter, Depends
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from api.dependencies import get_override_registry
from services.live_command import OverrideRegistry

router = APIRouter(prefix="/api/v1/overrides", tags=["Overrides"])


class OverrideStateResponse(BaseModel):
    device_id: str = Field(..., description="ID del dispositivo en override manual")
    mode: str = Field(..., description="Modo manual bloqueado ('MANUAL_ON', 'MANUAL_OFF', 'MANUAL_VALUE')")
    last_action: Optional[str] = Field(None, description="Última acción manual ejecutada")
    override_source: Optional[str] = Field(None, description="Origen de la orden (ej. usuario, API REST, UI)")
    set_at: float = Field(..., description="Timestamp de Unix de cuándo se activó el override")
    expires_at: Optional[float] = Field(None, description="Timestamp de Unix de cuándo expira el override (TTL), o null si es indefinido")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "device_id": "pump_01",
                "mode": "MANUAL_ON",
                "last_action": "turn_on",
                "override_source": "operador_sala_1",
                "set_at": 1725234500.0,
                "expires_at": None
            }
        }
    )


@router.get(
    "",
    response_model=List[OverrideStateResponse],
    summary="Listar dispositivos en modo manual (Overrides activos)",
    description="Retorna la lista de todos los actuadores que se encuentran bloqueados en control manual (`MANUAL_ON`, `MANUAL_OFF`, `MANUAL_VALUE`), indicando el usuario originario y el tiempo de expiración si aplica.",
)
async def list_active_overrides(override_reg: OverrideRegistry = Depends(get_override_registry)):
    overrides = override_reg.get_all_overrides()
    result = []
    for st in overrides:
        result.append({
            "device_id": st.device_id,
            "mode": st.mode.value,
            "last_action": st.last_action,
            "override_source": st.override_source,
            "set_at": st.set_at,
            "expires_at": st.expires_at,
        })
    return result
