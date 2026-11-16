import time
from typing import Dict, List, Optional
from services.live_command.models import ControlMode, DeviceControlState
from utils.logging import get_logger


class OverrideRegistry:
    """Persistent and thread-safe registry of device control modes and override states."""

    def __init__(self, db: Optional[Any] = None, event_bus: Optional[Any] = None):
        self._states: Dict[str, DeviceControlState] = {}
        self.db = db
        self.event_bus = event_bus
        self._logger = get_logger("OverrideRegistry")
        if self.db:
            self.load_from_db()

    def load_from_db(self) -> None:
        """Load persisted active overrides from database upon system initialization."""
        if not self.db or not getattr(self.db, "SessionFactory", None):
            return
        from storage.database import ActiveOverrideModel
        try:
            with self.db.get_session() as session:
                records = session.query(ActiveOverrideModel).all()
                now_ts = time.time()
                for r in records:
                    if r.expires_at is not None and now_ts > r.expires_at:
                        session.delete(r)
                        continue
                    try:
                        mode_enum = ControlMode(r.mode)
                    except ValueError:
                        mode_enum = ControlMode.AUTO
                    self._states[r.device_id] = DeviceControlState(
                        device_id=r.device_id,
                        mode=mode_enum,
                        last_action=r.last_action,
                        override_source=r.override_source,
                        set_at=r.set_at,
                        expires_at=r.expires_at,
                    )
                session.commit()
            if self._states:
                self._logger.info(
                    f"Restored {len(self._states)} active override(s) from persistent database."
                )
        except Exception as e:
            self._logger.warning(f"Could not load active overrides from database: {e}")

    def get_state(self, device_id: str) -> DeviceControlState:
        """Get or initialize the control state for a device."""
        if device_id not in self._states:
            self._states[device_id] = DeviceControlState(device_id=device_id, mode=ControlMode.AUTO)
        
        state = self._states[device_id]
        # Auto-expire TTL if set and elapsed
        if state.expires_at is not None and time.time() > state.expires_at:
            self._logger.info(f"Override TTL expired for device '{device_id}'. Reverting to AUTO.")
            prev_mode = state.mode
            state.mode = ControlMode.AUTO
            state.override_source = None
            state.expires_at = None

            if self.db and getattr(self.db, "SessionFactory", None):
                from storage.database import ActiveOverrideModel
                try:
                    with self.db.get_session() as session:
                        rec = session.get(ActiveOverrideModel, device_id)
                        if rec:
                            session.delete(rec)
                            session.commit()
                except Exception as e:
                    self._logger.warning(f"Could not delete expired override for '{device_id}': {e}")

            if self.event_bus:
                try:
                    import asyncio
                    loop = asyncio.get_running_loop()
                    loop.create_task(
                        self.event_bus.publish(
                            "override.expired",
                            sender="OverrideRegistry",
                            payload={
                                "device_id": device_id,
                                "mode": prev_mode.value,
                                "source": "TTL_EXPIRY",
                            },
                        )
                    )
                except RuntimeError:
                    pass

        return state

    def set_override(
        self,
        device_id: str,
        mode: ControlMode,
        action: str,
        source: Optional[str] = "LIVE_MANUAL",
        ttl_seconds: Optional[float] = None,
    ) -> DeviceControlState:
        """Set a manual override state for a device."""
        expires_at = (time.time() + ttl_seconds) if ttl_seconds else None
        state = DeviceControlState(
            device_id=device_id,
            mode=mode,
            last_action=action,
            override_source=source,
            set_at=time.time(),
            expires_at=expires_at,
        )
        self._states[device_id] = state
        self._logger.info(
            f"Override set for '{device_id}': mode={mode.value}, source={source}, action={action}"
        )

        if self.db and getattr(self.db, "SessionFactory", None):
            from storage.database import ActiveOverrideModel
            try:
                with self.db.get_session() as session:
                    rec = session.get(ActiveOverrideModel, device_id)
                    if not rec:
                        rec = ActiveOverrideModel(device_id=device_id)
                        session.add(rec)
                    rec.mode = mode.value
                    rec.last_action = action
                    rec.override_source = source
                    rec.set_at = state.set_at
                    rec.expires_at = expires_at
                    session.commit()
            except Exception as e:
                self._logger.warning(f"Could not persist override for '{device_id}': {e}")

        return state

    def restore_control(self, device_id: str) -> DeviceControlState:
        """Restore control of a device back to AUTO mode."""
        state = self.get_state(device_id)
        prev_mode = state.mode
        state.mode = ControlMode.AUTO
        state.override_source = None
        state.expires_at = None
        state.set_at = time.time()
        self._logger.info(f"Control restored to AUTO for device '{device_id}' (was {prev_mode.value})")

        if self.db and getattr(self.db, "SessionFactory", None):
            from storage.database import ActiveOverrideModel
            try:
                with self.db.get_session() as session:
                    rec = session.get(ActiveOverrideModel, device_id)
                    if rec:
                        session.delete(rec)
                        session.commit()
            except Exception as e:
                self._logger.warning(f"Could not remove persistent override for '{device_id}': {e}")

        return state

    def get_all_overrides(self) -> List[DeviceControlState]:
        """Return all devices currently under manual override."""
        active = []
        for dev_id in list(self._states.keys()):
            st = self.get_state(dev_id)
            if st.is_override_active():
                active.append(st)
        return active
