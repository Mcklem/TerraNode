from fastapi import APIRouter, Depends, HTTPException, status
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from api.dependencies import get_time_scheduler

router = APIRouter(prefix="/api/v1/schedules", tags=["Schedules"])


class ScheduleStateResponse(BaseModel):
    id: str = Field(..., description="ID de la programación (ej. 'riego_matutino_diario')")
    enabled: bool = Field(..., description="Indica si la programación está activa")
    device: str = Field(..., description="ID del actuador objetivo (ej. 'irrigation_pump')")
    command: str = Field(..., description="Comando de inicio a ejecutar (ej. 'turn_on', 'set_position')")
    stop_command: Optional[str] = Field(None, description="Comando de parada a ejecutar tras vencer la duración")
    duration_seconds: float = Field(0, description="Duración activa en segundos")
    is_duration_active: bool = Field(False, description="True si la tarea se encuentra actualmente dentro del periodo activo de duración")
    time: Optional[str] = Field(None, description="Hora de ejecución diaria 'HH:MM'")
    interval: Optional[float] = Field(None, description="Frecuencia de intervalo en segundos")
    cron: Optional[str] = Field(None, description="Expresión cron de 5 campos")
    days: Optional[List[str]] = Field(None, description="Lista de días de la semana activos")
    last_run_timestamp: Optional[float] = Field(None, description="Timestamp Unix de la última ejecución")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "riego_matutino_diario",
                "enabled": True,
                "device": "irrigation_pump",
                "command": "turn_on",
                "stop_command": "turn_off",
                "duration_seconds": 900,
                "is_duration_active": False,
                "time": "08:00",
                "interval": None,
                "cron": None,
                "days": ["mon", "tue", "wed", "thu", "fri"],
                "last_run_timestamp": 1725340800.0
            }
        }
    )


class TriggerResponse(BaseModel):
    success: bool = Field(..., description="Indica si el disparo manual de la tarea fue exitoso")
    schedule_id: str = Field(..., description="ID de la tarea programada")
    message: str = Field(..., description="Mensaje informativo del resultado")


@router.get(
    "",
    response_model=List[ScheduleStateResponse],
    summary="Listar tareas programadas por tiempo/calendario",
    description="Retorna el listado completo de tareas programadas temporales registradas en `TimeScheduler`, mostrando su frecuencia, hora de ejecución, estado y tiempo activo.",
)
async def list_schedules(time_scheduler: Any = Depends(get_time_scheduler)):
    return time_scheduler.get_schedule_states()


@router.post(
    "/{schedule_id}/trigger",
    response_model=TriggerResponse,
    summary="Disparar manualmente una tarea programada a demanda",
    description="Ejecuta de inmediato el comando de una tarea programada, iniciando su temporizador de duración si está configurado.",
    responses={
        404: {"description": "Programación no encontrada en la configuración activa."}
    }
)
async def trigger_schedule(
    schedule_id: str,
    time_scheduler: Any = Depends(get_time_scheduler),
):
    success = await time_scheduler.trigger_schedule(schedule_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to trigger schedule '{schedule_id}'. Device may be missing, disconnected, or locked in override mode."
        )
    return {
        "success": True,
        "schedule_id": schedule_id,
        "message": f"Successfully triggered schedule '{schedule_id}'",
    }


@router.post(
    "/{schedule_id}/toggle",
    response_model=Dict[str, Any],
    summary="Habilitar o pausar una tarea programada",
    description="Permite activar o desactivar dinámicamente una tarea programada sin reiniciar el sistema.",
    responses={
        404: {"description": "Programación no encontrada."}
    }
)
async def toggle_schedule(
    schedule_id: str,
    time_scheduler: Any = Depends(get_time_scheduler),
):
    cfg = time_scheduler.schedules_config.get(schedule_id)
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Schedule '{schedule_id}' not found")

    new_state = not cfg.get("enabled", True)
    cfg["enabled"] = new_state

    # If disabled, cancel any active duration timer
    if not new_state and schedule_id in time_scheduler._active_duration_tasks:
        task = time_scheduler._active_duration_tasks.get(schedule_id)
        if task and not task.done():
            task.cancel()

    return {
        "schedule_id": schedule_id,
        "enabled": new_state,
        "message": f"Schedule '{schedule_id}' is now {'enabled' if new_state else 'disabled'}",
    }
