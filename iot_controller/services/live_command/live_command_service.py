from typing import Any, Dict, List, Optional
from core.device_manager import DeviceManager
from core.node_manager import NodeManager
from services.live_command.command_dispatcher import CommandDispatcher
from services.live_command.models import (
    CommandExecutionResult,
    CommandSource,
    ControlMode,
    DeviceControlState,
    LiveCommandRequest,
)
from services.live_command.override_registry import OverrideRegistry
from utils.logging import get_logger


class LiveCommandService:
    """High-level Facade service for decoupled live node commands and manual overrides."""

    def __init__(
        self,
        device_manager: DeviceManager,
        node_manager: NodeManager,
        override_registry: Optional[OverrideRegistry] = None,
        dispatcher: Optional[CommandDispatcher] = None,
    ):
        self.device_manager = device_manager
        self.node_manager = node_manager
        self.override_registry = override_registry or OverrideRegistry()
        self.dispatcher = dispatcher or CommandDispatcher(
            device_manager=self.device_manager,
            override_registry=self.override_registry,
        )
        self._logger = get_logger("LiveCommandService")

    async def execute_live_command(
        self,
        device_id: str,
        action: str,
        params: Optional[Dict[str, Any]] = None,
        target_mode: Optional[ControlMode] = None,
        user_id: Optional[str] = "LIVE_OPERATOR",
        ttl_seconds: Optional[float] = None,
    ) -> CommandExecutionResult:
        """Execute an immediate manual command on a device and lock its override mode."""
        req = LiveCommandRequest(
            device_id=device_id,
            action=action,
            params=params or {},
            source=CommandSource.LIVE_MANUAL,
            target_mode=target_mode,
            user_id=user_id,
            ttl_seconds=ttl_seconds,
        )
        return await self.dispatcher.dispatch(req)

    async def restore_control(self, device_id: str) -> CommandExecutionResult:
        """Restore control of a device back to AUTO mode so rules can control it again."""
        state = self.override_registry.restore_control(device_id)
        device = self.device_manager.get_device(device_id)
        payload = device.get_state() if device else {}
        return CommandExecutionResult(
            success=True,
            device_id=device_id,
            applied_action="RESTORE_CONTROL",
            current_mode=state.mode,
            message=f"Restored automatic rule control (AUTO) for device '{device_id}'",
            state_payload=payload,
        )

    def get_control_state(self, device_id: str) -> DeviceControlState:
        """Fetch current control state and mode for a device."""
        return self.override_registry.get_state(device_id)

    def list_active_overrides(self) -> List[DeviceControlState]:
        """List all devices currently under manual override."""
        return self.override_registry.get_all_overrides()

    async def execute_raw_node_command(
        self,
        node_id: str,
        command_type: str,
        pin: str,
        value: Any,
    ) -> Dict[str, Any]:
        """Direct low-level command on a hardware node, completely bypassing device definitions."""
        node = self.node_manager.get_node(node_id)
        if not node or not node.is_connected():
            raise ValueError(f"Node '{node_id}' is not connected or registered.")

        if command_type == "digital_write":
            node.digital_write(pin, int(value))
        elif command_type == "analog_write":
            node.analog_write(pin, int(value))
        else:
            raise ValueError(f"Unsupported raw node command type '{command_type}'")

        self._logger.info(f"Raw node command sent to node '{node_id}' pin {pin}: {command_type}={value}")
        return {"node_id": node_id, "pin": pin, "command": command_type, "value": value}
