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
    ):
        self.rules_config = rules_config
        self.device_manager = device_manager
        self.event_bus = event_bus
        self.log_rule_evaluations = (
            log_rule_evaluations if log_rule_evaluations is not None else settings.log_rule_evaluations
        )
        self._running: bool = False
        self._logger = get_logger("RuleEngine")
        # Track active trigger state for each rule: rule_id -> bool
        self._rule_states: Dict[str, bool] = {}

    def start(self) -> None:
        """Subscribe to device value change events."""
        if self._running:
            return
        self._running = True
        self.event_bus.subscribe("device.value_changed", self._on_device_value_changed)
        self._logger.info(
            f"RuleEngine started with {len(self.rules_config)} rules configured (log_evaluations={self.log_rule_evaluations})."
        )

    def stop(self) -> None:
        """Unsubscribe from event bus."""
        self._running = False
        self.event_bus.unsubscribe("device.value_changed", self._on_device_value_changed)
        self._logger.info("RuleEngine stopped.")

    async def _on_device_value_changed(self, event: Event) -> None:
        """Evaluate all rules when a sensor measurement is published using edge triggering."""
        if not self._running:
            return

        payload = event.payload

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
                    self._rule_states[rule_id] = True
                    if self.log_rule_evaluations:
                        self._logger.info(
                            f"Rule '{rule_id}' [MATCH (Edge Trigger)]: {target_dev}.{prop} ({actual_val}) {op} {target_val} -> Executing {len(actions)} action(s)"
                        )
                    await self._execute_actions(rule_id, actions)
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

    async def _execute_actions(self, rule_id: str, actions: list) -> None:
        """Execute configured actuator actions."""
        for action in actions:
            target_id = action.get("device")
            command = action.get("command")
            args = action.get("args", {})

            if not target_id or not command:
                self._logger.warning(f"Rule '{rule_id}' action missing device or command.")
                continue

            device = self.device_manager.get_device(target_id)
            if not device:
                self._logger.error(f"Rule '{rule_id}' target device '{target_id}' not found.")
                continue

            try:
                cmd_func = getattr(device, command, None)
                if not callable(cmd_func):
                    self._logger.error(
                        f"Rule '{rule_id}': Device '{target_id}' has no command method '{command}'"
                    )
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
