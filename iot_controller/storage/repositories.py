import json
import time
from typing import Any, Dict, List
from sqlalchemy import delete
from core.event_bus import Event, EventBus
from storage.database import ActuatorHistoryModel, Database, EventModel, MeasurementModel
from utils.logging import get_logger


class StorageManager:
    """Subscribes to EventBus and manages persistent storage via SQLAlchemy ORM."""

    def __init__(self, db: Database, event_bus: EventBus):
        self.db = db
        self.event_bus = event_bus
        self._running: bool = False
        self._logger = get_logger("StorageManager")

    def start(self) -> None:
        """Subscribe to event bus topics."""
        if self._running:
            return
        self._running = True
        self.event_bus.subscribe("device.value_changed", self._on_measurement)
        self.event_bus.subscribe("*", self._on_any_event)
        self._logger.info("StorageManager started with SQLAlchemy ORM persistence.")

    def stop(self) -> None:
        self._running = False
        self.event_bus.unsubscribe("device.value_changed", self._on_measurement)
        self.event_bus.unsubscribe("*", self._on_any_event)
        self.db.close()
        self._logger.info("StorageManager stopped.")

    async def _on_measurement(self, event: Event) -> None:
        """Store sensor reading in measurements table using SQLAlchemy ORM."""
        payload = event.payload
        device_id = payload.get("id", event.sender)
        val = payload.get("value")
        unit = payload.get("unit", "")
        status = payload.get("status", "OK")
        ts = event.timestamp

        if val is not None:
            try:
                numeric_val = float(val)
            except (ValueError, TypeError):
                numeric_val = None

            def _save(session):
                measurement = MeasurementModel(
                    timestamp=ts,
                    device_id=device_id,
                    value=numeric_val,
                    unit=unit,
                    status=status,
                )
                session.add(measurement)

            await self.db.run_in_session(_save)

    async def _on_any_event(self, event: Event) -> None:
        """Log event to events table using SQLAlchemy ORM."""
        payload_str = json.dumps(event.payload, default=str)

        def _save(session):
            evt = EventModel(
                timestamp=event.timestamp,
                topic=event.topic,
                sender=event.sender,
                payload=payload_str,
            )
            session.add(evt)

        await self.db.run_in_session(_save)

    async def purge_old_data(self, retention_days: int = 30) -> int:
        """Delete historical measurements and events older than retention_days using SQLAlchemy ORM."""
        cutoff = time.time() - (retention_days * 86400)

        def _purge(session):
            session.execute(delete(MeasurementModel).where(MeasurementModel.timestamp < cutoff))
            session.execute(delete(EventModel).where(EventModel.timestamp < cutoff))

        await self.db.run_in_session(_purge)
        self._logger.info(f"Purged historical data older than {retention_days} days via SQLAlchemy ORM.")
        return retention_days
