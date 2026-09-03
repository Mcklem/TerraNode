from fastapi import APIRouter, Depends, Query
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import func, select
from api.dependencies import get_database
from storage.database import (
    ActuatorHistoryModel,
    Database,
    EventModel,
    MeasurementModel,
    NodeHistoryModel,
    ScheduleHistoryModel,
)

router = APIRouter(prefix="/api/v1/history", tags=["History"])

T = TypeVar("T")


class MeasurementRecord(BaseModel):
    id: int = Field(..., description="ID autoincremental de la lectura")
    timestamp: float = Field(..., description="Timestamp Unix de la lectura")
    device_id: str = Field(..., description="ID del sensor (ej. 'ldr_01', 'soil_01')")
    value: Optional[float] = Field(None, description="Valor numérico medido")
    unit: Optional[str] = Field(None, description="Unidad de medida ('raw', '%', '°C', 'hPa')")
    status: str = Field(..., description="Estado de la lectura ('OK', 'ERROR')")

    model_config = ConfigDict(from_attributes=True)


class ActuatorHistoryRecord(BaseModel):
    id: int = Field(..., description="ID autoincremental del registro")
    timestamp: float = Field(..., description="Timestamp Unix del cambio de estado")
    device_id: str = Field(..., description="ID del actuador (ej. 'pump_01', 'vent_servo')")
    state: str = Field(..., description="Acción o estado aplicado ('turn_on', 'turn_off', 'ANGLE_90')")
    source: Optional[str] = Field(None, description="Origen de la orden ('LIVE_MANUAL', 'RULE_ENGINE', 'SYSTEM')")
    user_id: Optional[str] = Field(None, description="Operador o regla originaria del comando")

    model_config = ConfigDict(from_attributes=True)


class NodeHistoryRecord(BaseModel):
    id: int = Field(..., description="ID autoincremental del evento de conexión")
    timestamp: float = Field(..., description="Timestamp Unix del evento")
    node_id: str = Field(..., description="ID del nodo hardware (ej. 'weather_01')")
    host: str = Field(..., description="Dirección IP del nodo")
    port: int = Field(..., description="Puerto TCP de comunicación")
    driver: str = Field(..., description="Driver del nodo ('firmata', 'mock')")
    event: str = Field(..., description="Evento de conexión ('CONNECTED', 'DISCONNECTED', 'RECONNECTING')")

    model_config = ConfigDict(from_attributes=True)


class EventRecord(BaseModel):
    id: int = Field(..., description="ID autoincremental del evento")
    timestamp: float = Field(..., description="Timestamp Unix del evento")
    topic: str = Field(..., description="Tópico del evento publicado en EventBus")
    sender: str = Field(..., description="Emisor o componente origen del evento")
    payload: str = Field(..., description="Payload en formato JSON formateado como cadena")

    model_config = ConfigDict(from_attributes=True)


class ScheduleHistoryRecord(BaseModel):
    id: int = Field(..., description="ID autoincremental de la ejecución")
    timestamp: float = Field(..., description="Timestamp Unix del disparo o finalización")
    schedule_id: str = Field(..., description="ID de la tarea programada (ej. 'riego_matutino')")
    device_id: str = Field(..., description="ID del actuador objetivo (ej. 'irrigation_pump')")
    action: str = Field(..., description="Comando o acción ejecutada ('turn_on', 'turn_off')")
    event_type: str = Field(..., description="Fase de la ejecución ('TRIGGERED', 'COMPLETED', 'BLOCKED')")
    duration: Optional[float] = Field(None, description="Duración activa configurada en segundos")
    status: str = Field(..., description="Resultado de la ejecución ('SUCCESS', 'BLOCKED', 'FAILED')")

    model_config = ConfigDict(from_attributes=True)


class PaginatedMeasurementsResponse(BaseModel):
    total: int = Field(..., description="Número total de registros coincidentes en la base de datos")
    limit: int = Field(..., description="Límite máximo de registros retornados en la página")
    offset: int = Field(..., description="Número de registros desplazados/omitidos")
    data: List[MeasurementRecord] = Field(..., description="Lista de mediciones de sensores")


class PaginatedActuatorsResponse(BaseModel):
    total: int = Field(..., description="Número total de registros de actuadores")
    limit: int = Field(..., description="Límite de registros devueltos")
    offset: int = Field(..., description="Desplazamiento inicial de la consulta")
    data: List[ActuatorHistoryRecord] = Field(..., description="Lista de eventos de actuadores")


class PaginatedNodesResponse(BaseModel):
    total: int = Field(..., description="Número total de registros de conexión de nodos")
    limit: int = Field(..., description="Límite de registros devueltos")
    offset: int = Field(..., description="Desplazamiento inicial de la consulta")
    data: List[NodeHistoryRecord] = Field(..., description="Lista de eventos de nodos")


class PaginatedEventsResponse(BaseModel):
    total: int = Field(..., description="Número total de eventos del sistema")
    limit: int = Field(..., description="Límite de registros devueltos")
    offset: int = Field(..., description="Desplazamiento inicial de la consulta")
    data: List[EventRecord] = Field(..., description="Lista de auditoría de eventos")


class PaginatedSchedulesHistoryResponse(BaseModel):
    total: int = Field(..., description="Número total de registros de auditoría de schedules")
    limit: int = Field(..., description="Límite de registros devueltos")
    offset: int = Field(..., description="Desplazamiento inicial de la consulta")
    data: List[ScheduleHistoryRecord] = Field(..., description="Lista de eventos del scheduler")


@router.get(
    "/measurements",
    response_model=PaginatedMeasurementsResponse,
    summary="Consultar historial de telemetría de sensores (Paginado)",
    description="Retorna las lecturas históricas almacenadas de los sensores con soporte para filtrado por `device_id` y paginación (`limit`, `offset`), ordenadas de más reciente a más antigua.",
)
async def get_measurements_history(
    device_id: Optional[str] = Query(None, description="Filtrar por ID específico de sensor (ej. 'ldr_01')"),
    order: str = Query("desc", description="Orden de clasificación por fecha ('desc' o 'asc')"),
    limit: int = Query(50, ge=1, le=500, description="Cantidad máxima de registros a retornar"),
    offset: int = Query(0, ge=0, description="Número de registros a omitir para paginación"),
    db: Database = Depends(get_database),
):
    def _query(session):
        stmt_count = select(func.count(MeasurementModel.id))
        order_clause = MeasurementModel.timestamp.asc() if order == "asc" else MeasurementModel.timestamp.desc()
        stmt_data = select(MeasurementModel).order_by(order_clause)

        if device_id:
            stmt_count = stmt_count.where(MeasurementModel.device_id == device_id)
            stmt_data = stmt_data.where(MeasurementModel.device_id == device_id)

        total = session.scalar(stmt_count) or 0
        records = session.scalars(stmt_data.limit(limit).offset(offset)).all()
        return total, records

    total, records = await db.run_in_session(_query)
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [MeasurementRecord.model_validate(r) for r in records],
    }


@router.get(
    "/actuators",
    response_model=PaginatedActuatorsResponse,
    summary="Consultar historial de comandos de actuadores (Paginado)",
    description="Retorna el registro histórico de cambios de estado y órdenes ejecutadas en los actuadores con filtrado opcional por `device_id` o `source` y paginación.",
)
async def get_actuators_history(
    device_id: Optional[str] = Query(None, description="Filtrar por ID específico de actuador (ej. 'pump_01')"),
    source: Optional[str] = Query(None, description="Filtrar por origen del comando ('LIVE_MANUAL', 'RULE_ENGINE', 'SCHEDULER')"),
    limit: int = Query(50, ge=1, le=500, description="Cantidad máxima de registros"),
    offset: int = Query(0, ge=0, description="Desplazamiento inicial"),
    db: Database = Depends(get_database),
):
    def _query(session):
        stmt_count = select(func.count(ActuatorHistoryModel.id))
        stmt_data = select(ActuatorHistoryModel).order_by(ActuatorHistoryModel.timestamp.desc())

        if device_id:
            stmt_count = stmt_count.where(ActuatorHistoryModel.device_id == device_id)
            stmt_data = stmt_data.where(ActuatorHistoryModel.device_id == device_id)
        if source:
            stmt_count = stmt_count.where(ActuatorHistoryModel.source == source)
            stmt_data = stmt_data.where(ActuatorHistoryModel.source == source)

        total = session.scalar(stmt_count) or 0
        records = session.scalars(stmt_data.limit(limit).offset(offset)).all()
        return total, records

    total, records = await db.run_in_session(_query)
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [ActuatorHistoryRecord.model_validate(r) for r in records],
    }


@router.get(
    "/nodes",
    response_model=PaginatedNodesResponse,
    summary="Consultar historial de conexión de nodos (Paginado)",
    description="Retorna la bitácora histórica de eventos de conexión y direccionamiento IP de nodos hardware con filtrado por `node_id` y paginación.",
)
async def get_nodes_history(
    node_id: Optional[str] = Query(None, description="Filtrar por ID específico de nodo (ej. 'weather_01')"),
    limit: int = Query(50, ge=1, le=500, description="Cantidad máxima de registros"),
    offset: int = Query(0, ge=0, description="Desplazamiento inicial"),
    db: Database = Depends(get_database),
):
    def _query(session):
        stmt_count = select(func.count(NodeHistoryModel.id))
        stmt_data = select(NodeHistoryModel).order_by(NodeHistoryModel.timestamp.desc())

        if node_id:
            stmt_count = stmt_count.where(NodeHistoryModel.node_id == node_id)
            stmt_data = stmt_data.where(NodeHistoryModel.node_id == node_id)

        total = session.scalar(stmt_count) or 0
        records = session.scalars(stmt_data.limit(limit).offset(offset)).all()
        return total, records

    total, records = await db.run_in_session(_query)
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [NodeHistoryRecord.model_validate(r) for r in records],
    }


@router.get(
    "/schedules",
    response_model=PaginatedSchedulesHistoryResponse,
    summary="Consultar historial de ejecuciones del scheduler (Paginado)",
    description="Retorna la bitácora histórica de disparos (`TRIGGERED`), expiraciones de duración (`COMPLETED`) y bloqueos (`BLOCKED`) de tareas temporales del `TimeScheduler`.",
)
async def get_schedules_history(
    schedule_id: Optional[str] = Query(None, description="Filtrar por ID de tarea programada (ej. 'riego_matutino')"),
    device_id: Optional[str] = Query(None, description="Filtrar por ID de actuador objetivo (ej. 'irrigation_pump')"),
    limit: int = Query(50, ge=1, le=500, description="Cantidad máxima de registros"),
    offset: int = Query(0, ge=0, description="Desplazamiento inicial"),
    db: Database = Depends(get_database),
):
    def _query(session):
        stmt_count = select(func.count(ScheduleHistoryModel.id))
        stmt_data = select(ScheduleHistoryModel).order_by(ScheduleHistoryModel.timestamp.desc())

        if schedule_id:
            stmt_count = stmt_count.where(ScheduleHistoryModel.schedule_id == schedule_id)
            stmt_data = stmt_data.where(ScheduleHistoryModel.schedule_id == schedule_id)
        if device_id:
            stmt_count = stmt_count.where(ScheduleHistoryModel.device_id == device_id)
            stmt_data = stmt_data.where(ScheduleHistoryModel.device_id == device_id)

        total = session.scalar(stmt_count) or 0
        records = session.scalars(stmt_data.limit(limit).offset(offset)).all()
        return total, records

    total, records = await db.run_in_session(_query)
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [ScheduleHistoryRecord.model_validate(r) for r in records],
    }


@router.get(
    "/events",
    response_model=PaginatedEventsResponse,
    summary="Consultar auditoría general de eventos del sistema (Paginado)",
    description="Retorna el registro histórico de auditoría de eventos publicados en el bus pub-sub del sistema con filtrado opcional por `topic` y paginación.",
)
async def get_events_history(
    topic: Optional[str] = Query(None, description="Filtrar por tópico exacto de evento (ej. 'rule.triggered')"),
    limit: int = Query(50, ge=1, le=500, description="Cantidad máxima de registros"),
    offset: int = Query(0, ge=0, description="Desplazamiento inicial"),
    db: Database = Depends(get_database),
):
    def _query(session):
        stmt_count = select(func.count(EventModel.id))
        stmt_data = select(EventModel).order_by(EventModel.timestamp.desc())

        if topic:
            stmt_count = stmt_count.where(EventModel.topic == topic)
            stmt_data = stmt_data.where(EventModel.topic == topic)

        total = session.scalar(stmt_count) or 0
        records = session.scalars(stmt_data.limit(limit).offset(offset)).all()
        return total, records

    total, records = await db.run_in_session(_query)
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [EventRecord.model_validate(r) for r in records],
    }
