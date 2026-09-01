import time
from typing import Dict, List, Optional
from services.live_command.models import ControlMode, DeviceControlState
from utils.logging import get_logger


class OverrideRegistry:
    """Decoupled in-memory registry of device control modes and override states."""

    def __init__(self):
        self._states: Dict[str, DeviceControlState] = {}
        self._logger = get_logger("OverrideRegistry")

    def get_state(self, device_id: str) -> DeviceControlState:
        """Get or initialize the control state for a device."""
        if device_id not in self._states:
            self._states[device_id] = DeviceControlState(device_id=device_id, mode=ControlMode.AUTO)
        
        state = self._states[device_id]
        # Auto-expire TTL if set and elapsed
        if state.expires_at is not None and time.time() > state.expires_at:
            self._logger.info(f"Override TTL expired for device '{device_id}'. Reverting to AUTO.")
            state.mode = ControlMode.AUTO
            state.override_source = None
            state.expires_at = None

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
        return state

    def get_all_overrides(self) -> List[DeviceControlState]:
        """Return all devices currently under manual override."""
        active = []
        for dev_id in list(self._states.keys()):
            st = self.get_state(dev_id)
            if st.is_override_active():
                active.append(st)
        return active
