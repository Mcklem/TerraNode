import asyncio
import inspect
from typing import Any, Dict, Optional
from core.device_manager import DeviceManager
from core.event_bus import Event, EventBus
from services.live_command.models import (
    CommandExecutionResult,
    CommandSource,
    ControlMode,
    LiveCommandRequest,
)
from services.live_command.override_registry import OverrideRegistry
from utils.logging import get_logger


class CommandDispatcher:
    """Command Mediator & Gateway enforcing live override priority over automated rules."""

    def __init__(
        self,
        device_manager: DeviceManager,
        override_registry: OverrideRegistry,
        event_bus: Optional[EventBus] = None,
    ):
        self.device_manager = device_manager
        self.override_registry = override_registry
        self.event_bus = event_bus
        self._logger = get_logger("CommandDispatcher")

    async def dispatch(self, request: LiveCommandRequest) -> CommandExecutionResult:
        """Dispatch a command request after checking priority and override state."""
        device_id = request.device_id
        action_name = request.action
        source = request.source

        device = self.device_manager.get_device(device_id)
        if not device:
            return CommandExecutionResult(
                success=False,
                device_id=device_id,
                applied_action=action_name,
                current_mode=ControlMode.AUTO,
                message=f"Device '{device_id}' not found in DeviceManager",
            )

        current_state = self.override_registry.get_state(device_id)

        # Priority Evaluation
        if source in (CommandSource.RULE_ENGINE, CommandSource.SCHEDULER):
            if current_state.is_override_active():
                msg = (
                    f"Command '{action_name}' from {source.value} BLOCKED on '{device_id}'. "
                    f"Device is locked in manual override mode '{current_state.mode.value}' "
                    f"by {current_state.override_source or 'Operator'}."
                )
                self._logger.warning(msg)
                
                # Emit event if bus available
                if self.event_bus:
                    await self.event_bus.publish(
                        "command.blocked",
                        sender="CommandDispatcher",
                        payload={
                            "device_id": device_id,
                            "attempted_action": action_name,
                            "source": source.value,
                            "override_mode": current_state.mode.value,
                        },
                    )

                return CommandExecutionResult(
                    success=False,
                    device_id=device_id,
                    applied_action=action_name,
                    current_mode=current_state.mode,
                    message=msg,
                    state_payload=device.get_state(),
                )

        # Determine target mode if this is a live manual command
        target_mode = request.target_mode
        if source == CommandSource.LIVE_MANUAL and target_mode is None:
            if action_name in ("turn_on", "ON", "1"):
                target_mode = ControlMode.MANUAL_ON
            elif action_name in ("turn_off", "OFF", "0"):
                target_mode = ControlMode.MANUAL_OFF
            else:
                target_mode = ControlMode.MANUAL_VALUE

        # Execute hardware command on device
        action_method = getattr(device, action_name, None)
        if not action_method or not callable(action_method):
            return CommandExecutionResult(
                success=False,
                device_id=device_id,
                applied_action=action_name,
                current_mode=current_state.mode,
                message=f"Device '{device_id}' does not support action '{action_name}'",
            )

        try:
            if inspect.iscoroutinefunction(action_method):
                res_payload = await action_method(**request.params)
            else:
                res_payload = action_method(**request.params)

            # Update override state if command was live manual
            if source == CommandSource.LIVE_MANUAL and target_mode:
                updated_state = self.override_registry.set_override(
                    device_id=device_id,
                    mode=target_mode,
                    action=action_name,
                    source=request.user_id or "LIVE_MANUAL",
                    ttl_seconds=request.ttl_seconds,
                )
                current_mode = updated_state.mode
            else:
                current_mode = current_state.mode

            if self.event_bus:
                await self.event_bus.publish(
                    "command.executed",
                    sender="CommandDispatcher",
                    payload={
                        "device_id": device_id,
                        "action": action_name,
                        "source": source.value,
                        "mode": current_mode.value,
                    },
                )

            return CommandExecutionResult(
                success=True,
                device_id=device_id,
                applied_action=action_name,
                current_mode=current_mode,
                message=f"Successfully executed '{action_name}' on device '{device_id}'",
                state_payload=res_payload or device.get_state(),
            )

        except Exception as e:
            self._logger.error(f"Error executing '{action_name}' on device '{device_id}': {e}")
            return CommandExecutionResult(
                success=False,
                device_id=device_id,
                applied_action=action_name,
                current_mode=current_state.mode,
                message=f"Execution error on '{device_id}': {e}",
            )
