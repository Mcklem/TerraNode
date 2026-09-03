import asyncio
from typing import Any, Dict, Optional
from automation.conditions import evaluate_condition
from core.device_manager import DeviceManager
from core.event_bus import Event, EventBus
from core.settings import settings
from devices.actuator import Actuator
from utils.logging import get_logger


class RuleEngine:
    """Hardware-agnostic edge-triggered automation rule evaluator and executor."""

    def __init__(
        self,
        rules_config: Dict[str, dict],
        device_manager: DeviceManager,
        event_bus: EventBus,
        log_rule_evaluations: Optional[bool] = None,
        command_dispatcher: Optional[Any] = None,
    ):
        self.rules_config = rules_config
        self.device_manager = device_manager
        self.event_bus = event_bus
        self.command_dispatcher = command_dispatcher
        self.log_rule_evaluations = (
            log_rule_evaluations if log_rule_evaluations is not None else settings.log_rule_evaluations
        )
        self._running: bool = False
        self._logger = get_logger("RuleEngine")
        # Track active trigger state for each rule: rule_id -> bool
        self._rule_states: Dict[str, bool] = {}
        # Cache latest sensor payloads for immediate re-evaluation when control is restored
        self._last_sensor_payloads: Dict[str, dict] = {}

    def start(self) -> None:
        """Subscribe to device value change and control restored events."""
        if self._running:
            return
        self._running = True
        self.event_bus.subscribe("device.value_changed", self._on_device_value_changed)
        self.event_bus.subscribe("device.control_restored", self._on_device_control_restored)
        self._logger.info(
            f"RuleEngine started with {len(self.rules_config)} rules configured (log_evaluations={self.log_rule_evaluations})."
        )

    def stop(self) -> None:
        """Unsubscribe from event bus."""
        self._running = False
        self.event_bus.unsubscribe("device.value_changed", self._on_device_value_changed)
        self.event_bus.unsubscribe("device.control_restored", self._on_device_control_restored)
        self._logger.info("RuleEngine stopped.")

    def get_rule_states(self) -> list:
        """Return real-time state and configuration for all configured rules."""
        states = []
        for rule_id, cfg in self.rules_config.items():
            cond = cfg.get("condition", {})
            actions = cfg.get("actions", [])
            is_triggered = self._rule_states.get(rule_id, False)
            sensor_id = cond.get("device")
            last_sensor_value = None
            if sensor_id and sensor_id in self._last_sensor_payloads:
                prop = cond.get("property", "value")
                last_sensor_value = self._last_sensor_payloads[sensor_id].get(prop)

            states.append({
                "id": rule_id,
                "enabled": cfg.get("enabled", True),
                "condition": cond,
                "actions": actions,
                "retrigger": cfg.get("retrigger", False),
                "is_triggered": is_triggered,
                "last_sensor_value": last_sensor_value,
            })
        return states

    def toggle_rule(self, rule_id: str) -> Optional[bool]:
        """Dynamically enable or pause a rule."""
        cfg = self.rules_config.get(rule_id)
        if not cfg:
            return None
        new_state = not cfg.get("enabled", True)
        cfg["enabled"] = new_state
        if not new_state:
            self._rule_states[rule_id] = False
        return new_state

    async def _on_device_control_restored(self, event: Event) -> None:
        """Re-evaluate rules immediately when manual override is released (restored to AUTO)."""
        if not self._running:
            return

        restored_device_id = event.payload.get("device_id")
        if not restored_device_id:
            return

        self._logger.info(
            f"Control restored to AUTO for device '{restored_device_id}'. Re-evaluating rules..."
        )

        for rule_id, rule_cfg in self.rules_config.items():
            if not rule_cfg.get("enabled", True):
                continue

            actions = rule_cfg.get("actions", [])
            if any(act.get("device") == restored_device_id for act in actions):
                # Reset rule state so edge-triggering permits immediate re-evaluation
                self._rule_states[rule_id] = False

                # Re-evaluate rule if sensor reading is cached
                cond = rule_cfg.get("condition", {})
                sensor_id = cond.get("device")
                if sensor_id and sensor_id in self._last_sensor_payloads:
                    mock_evt = Event(
                        topic="device.value_changed",
                        sender=sensor_id,
                        payload=self._last_sensor_payloads[sensor_id],
                    )
                    await self._on_device_value_changed(mock_evt)

    async def _on_device_value_changed(self, event: Event) -> None:
        """Evaluate all rules when a sensor measurement is published using edge triggering."""
        if not self._running:
            return

        payload = event.payload
        self._last_sensor_payloads[event.sender] = payload

        for rule_id, rule_cfg in self.rules_config.items():
            if not rule_cfg.get("enabled", True):
                continue

            cond = rule_cfg.get("condition", {})
            target_dev = cond.get("device")

            if target_dev and event.sender != target_dev:
                continue

            matched = evaluate_condition(cond, payload)
            prop = cond.get("property", "value")
            actual_val = payload.get(prop)
            op = cond.get("operator", "==")
            target_val = cond.get("value")
            actions = rule_cfg.get("actions", [])
            retrigger = rule_cfg.get("retrigger", False)

            was_triggered = self._rule_states.get(rule_id, False)

            if matched:
                if not was_triggered or retrigger:
                    if self.log_rule_evaluations:
                        self._logger.info(
                            f"Rule '{rule_id}' [MATCH (Edge Trigger)]: {target_dev}.{prop} ({actual_val}) {op} {target_val} -> Executing {len(actions)} action(s)"
                        )
                    success = await self._execute_actions(rule_id, actions)
                    if success:
                        self._rule_states[rule_id] = True
                    else:
                        # Actions blocked by live override dispatcher -> keep rule state as False
                        self._rule_states[rule_id] = False
                else:
                    if self.log_rule_evaluations:
                        self._logger.debug(
                            f"Rule '{rule_id}' [SUSTAINED MATCH]: {target_dev}.{prop} ({actual_val}) {op} {target_val} -> Condition remains active (skipping duplicate execution)."
                        )
            else:
                if was_triggered:
                    self._rule_states[rule_id] = False
                    if self.log_rule_evaluations:
                        self._logger.info(
                            f"Rule '{rule_id}' [RESET]: Condition {target_dev}.{prop} ({actual_val}) {op} {target_val} no longer matches -> Resetting rule state."
                        )
                else:
                    if self.log_rule_evaluations:
                        self._logger.debug(
                            f"Rule '{rule_id}' [NO MATCH]: {target_dev}.{prop} ({actual_val}) {op} {target_val}"
                        )

    async def _execute_actions(self, rule_id: str, actions: list) -> bool:
        """Execute configured actuator actions. Returns True if all actions succeeded."""
        all_succeeded = True

        for action in actions:
            target_id = action.get("device")
            command = action.get("command")
            args = action.get("args", {})

            if not target_id or not command:
                self._logger.warning(f"Rule '{rule_id}' action missing device or command.")
                all_succeeded = False
                continue

            if self.command_dispatcher:
                from services.live_command.models import CommandSource, LiveCommandRequest
                req = LiveCommandRequest(
                    device_id=target_id,
                    action=command,
                    params=args,
                    source=CommandSource.RULE_ENGINE,
                    user_id=f"rule:{rule_id}",
                )
                res = await self.command_dispatcher.dispatch(req)
                if res.success:
                    await self.event_bus.publish(
                        topic="rule.triggered",
                        sender=rule_id,
                        payload={"rule_id": rule_id, "action": action, "result": res.state_payload},
                    )
                else:
                    self._logger.info(
                        f"Rule '{rule_id}' action on '{target_id}' blocked by command dispatcher: {res.message}"
                    )
                    all_succeeded = False
                continue

            device = self.device_manager.get_device(target_id)
            if not device:
                self._logger.error(f"Rule '{rule_id}' target device '{target_id}' not found.")
                all_succeeded = False
                continue

            try:
                cmd_func = getattr(device, command, None)
                if not callable(cmd_func):
                    self._logger.error(
                        f"Rule '{rule_id}': Device '{target_id}' has no command method '{command}'"
                    )
                    all_succeeded = False
                    continue

                self._logger.info(f"Rule '{rule_id}' action -> {target_id}.{command}({args if args else ''})")
                res = cmd_func(**args) if args else cmd_func()
                if asyncio.iscoroutine(res):
                    res = await res

                await self.event_bus.publish(
                    topic="rule.triggered",
                    sender=rule_id,
                    payload={"rule_id": rule_id, "action": action, "result": res},
                )
            except Exception as e:
                self._logger.error(f"Error executing action for rule '{rule_id}' on '{target_id}': {e}")
                all_succeeded = False

        return all_succeeded
