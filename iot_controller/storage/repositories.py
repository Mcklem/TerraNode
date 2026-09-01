import asyncio
import json
import time
from typing import Any, Dict, List, Optional
from sqlalchemy import delete
from core.event_bus import Event, EventBus
from storage.database import ActuatorHistoryModel, Database, EventModel, MeasurementModel
from utils.logging import get_logger


class StorageManager:
    """Subscribes to EventBus and manages queued persistent storage via SQLAlchemy ORM."""

    def __init__(self, db: Database, event_bus: EventBus):
        self.db = db
        self.event_bus = event_bus
        self._running: bool = False
        self._queue: asyncio.Queue = asyncio.Queue()
        self._writer_task: Optional[asyncio.Task] = None
        self._logger = get_logger("StorageManager")

    def start(self) -> None:
        """Subscribe to event bus topics and launch batch write worker."""
        if self._running:
            return
        self._running = True
        self._writer_task = asyncio.create_task(self._writer_loop())
        self.event_bus.subscribe("device.value_changed", self._on_measurement)
        self.event_bus.subscribe("*", self._on_any_event)
        self._logger.info("StorageManager started with queued SQLAlchemy ORM persistence.")

    def stop(self) -> None:
        """Stop subscriptions, drain write queue, and close database."""
        if not self._running:
            return
        self._running = False
        self.event_bus.unsubscribe("device.value_changed", self._on_measurement)
        self.event_bus.unsubscribe("*", self._on_any_event)

        if self._writer_task:
            self._writer_task.cancel()
            self._writer_task = None

        # Final synchronous flush of leftover items in queue
        self._flush_queue_sync()
        self.db.close()
        self._logger.info("StorageManager stopped.")

    async def _on_measurement(self, event: Event) -> None:
        """Queue sensor reading for batch storage in measurements table."""
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

            measurement = MeasurementModel(
                timestamp=ts,
                device_id=device_id,
                value=numeric_val,
                unit=unit,
                status=status,
            )
            await self._queue.put(measurement)

    async def _on_any_event(self, event: Event) -> None:
        """Queue event for batch storage in events table (skipping redundant device.value_changed)."""
        if event.topic == "device.value_changed":
            return  # Already handled in structured measurements table

        payload_str = json.dumps(event.payload, default=str)
        evt = EventModel(
            timestamp=event.timestamp,
            topic=event.topic,
            sender=event.sender,
            payload=payload_str,
        )
        await self._queue.put(evt)

    async def _writer_loop(self) -> None:
        """Background worker loop that processes queued database models in batches."""
        while self._running:
            try:
                batch = []
                # Block until at least one item arrives
                item = await self._queue.get()
                batch.append(item)
                self._queue.task_done()

                # Drain any additional pending items up to 50
                while len(batch) < 50 and not self._queue.empty():
                    item = self._queue.get_nowait()
                    batch.append(item)
                    self._queue.task_done()

                if batch:
                    await self._save_batch(batch)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Error in StorageManager batch writer: {e}")

    async def _save_batch(self, batch: List[Any]) -> None:
        """Save a batch of ORM models inside a single session transaction."""
        def _commit_batch(session):
            session.add_all(batch)

        try:
            await self.db.run_in_session(_commit_batch)
        except Exception as e:
            self._logger.error(f"Failed to commit batch of {len(batch)} items: {e}")

    def _flush_queue_sync(self) -> None:
        """Synchronously flush remaining queued items during shutdown."""
        items = []
        while not self._queue.empty():
            items.append(self._queue.get_nowait())

        if items and self.db.SessionFactory:
            try:
                with self.db.get_session() as session:
                    session.add_all(items)
                    session.commit()
                self._logger.debug(f"Flushed {len(items)} items to database during shutdown.")
            except Exception as e:
                self._logger.warning(f"Error flushing queue during shutdown: {e}")

    async def purge_old_data(self, retention_days: int = 30) -> int:
        """Delete historical measurements and events older than retention_days using SQLAlchemy ORM."""
        cutoff = time.time() - (retention_days * 86400)

        def _purge(session):
            session.execute(delete(MeasurementModel).where(MeasurementModel.timestamp < cutoff))
            session.execute(delete(EventModel).where(EventModel.timestamp < cutoff))

        await self.db.run_in_session(_purge)
        self._logger.info(f"Purged historical data older than {retention_days} days via SQLAlchemy ORM.")
        return retention_days
