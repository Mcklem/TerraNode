from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
import time


class ControlMode(str, Enum):
    """Logical control state modes for devices/actuators."""
    AUTO = "AUTO"
    MANUAL_ON = "MANUAL_ON"
    MANUAL_OFF = "MANUAL_OFF"
    MANUAL_VALUE = "MANUAL_VALUE"


class CommandSource(str, Enum):
    """Source origin of actuator command requests."""
    LIVE_MANUAL = "LIVE_MANUAL"
    RULE_ENGINE = "RULE_ENGINE"
    SCHEDULER = "SCHEDULER"
    SYSTEM = "SYSTEM"


@dataclass
class DeviceControlState:
    """Represents the current control mode and override state for a device."""
    device_id: str
    mode: ControlMode = ControlMode.AUTO
    last_action: Optional[str] = None
    override_source: Optional[str] = None
    set_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None

    def is_override_active(self) -> bool:
        """Returns True if the device is locked in manual override mode and not expired."""
        if self.mode == ControlMode.AUTO:
            return False
        if self.expires_at is not None and time.time() > self.expires_at:
            return False
        return True


@dataclass
class LiveCommandRequest:
    """Data transfer object for live command execution requests."""
    device_id: str
    action: str  # e.g., 'turn_on', 'turn_off', 'set_position', 'toggle'
    params: Dict[str, Any] = field(default_factory=dict)
    source: CommandSource = CommandSource.LIVE_MANUAL
    target_mode: Optional[ControlMode] = None
    user_id: Optional[str] = None
    ttl_seconds: Optional[float] = None


@dataclass
class CommandExecutionResult:
    """Data transfer object for command execution outcomes."""
    success: bool
    device_id: str
    applied_action: str
    current_mode: ControlMode
    message: str
    state_payload: Dict[str, Any] = field(default_factory=dict)
