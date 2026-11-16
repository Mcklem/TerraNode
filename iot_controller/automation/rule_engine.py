import asyncio
from datetime import datetime
from typing import Any, Dict, Optional
from automation.conditions import evaluate_condition
from core.device_manager import DeviceManager
from core.event_bus import Event, EventBus
from core.settings import settings
from devices.actuator import Actuator
from utils.logging import get_logger


def _format_template_string(template_str: str, context: Dict[str, Any]) -> str:
    """Substitute {key} placeholders using provided context dictionary."""
    res = template_str
    for k, v in context.items():
        placeholder = "{" + str(k) + "}"
        if placeholder in res:
            res = res.replace(placeholder, str(v))
    return res


class RuleEngine:
    """Hardware-agnostic edge-triggered automation rule evaluator and executor."""

    def __init__(
        self,
        rules_config: Dict[str, dict],
        device_manager: DeviceManager,
        event_bus: EventBus,
        log_rule_evaluations: Optional[bool] = None,
        command_dispatcher: Optional[Any] = None,
        notification_service: Optional[Any] = None,
    ):
        self.rules_config = rules_config
        self.device_manager = device_manager
        self.event_bus = event_bus
        self.command_dispatcher = command_dispatcher
        self.notification_service = notification_service
        self.log_rule_evaluations = (
            log_rule_evaluations if log_rule_evaluations is not None else settings.log_rule_evaluations
        )
        self._running: bool = False
        self._logger = get_logger("RuleEngine")
        # Track active trigger state for each rule: rule_id -> bool
        self._rule_states: Dict[str, bool] = {}
        # Track last notification dispatch time for anti-spam cooldown: rule_id -> timestamp (seconds)
        self._last_notified_timestamps: Dict[str, float] = {}
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
                "cooldown": cfg.get("cooldown"),
                "recovery_message": cfg.get("recovery_message"),
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

            was_triggered = self._rule_states.get(rule_id, False)
            matched = evaluate_condition(cond, payload, is_currently_triggered=was_triggered)
            prop = cond.get("property", "value")
            actual_val = payload.get(prop)
            op = cond.get("operator", "==")
            target_val = cond.get("value")
            actions = rule_cfg.get("actions", [])
            retrigger = rule_cfg.get("retrigger", False)

            ctx = {
                "rule_id": rule_id,
                "device": target_dev,
                "property": prop,
                "value": actual_val,
                "operator": op,
                "threshold": target_val,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }

            if matched:
                cooldown = float(rule_cfg.get("cooldown", 0))
                now_time = asyncio.get_running_loop().time()
                last_notified = self._last_notified_timestamps.get(rule_id, 0.0)
                in_cooldown = (now_time - last_notified) < cooldown if cooldown > 0 else False

                if not was_triggered or retrigger:
                    if self.log_rule_evaluations:
                        self._logger.info(
                            f"Rule '{rule_id}' [MATCH (Edge Trigger)]: {target_dev}.{prop} ({actual_val}) {op} {target_val} -> Executing {len(actions)} action(s)"
                        )
                    success = await self._execute_actions(
                        rule_id,
                        actions,
                        context=ctx,
                        skip_notifications=in_cooldown,
                    )
                    if success:
                        self._rule_states[rule_id] = True
                        if not in_cooldown:
                            self._last_notified_timestamps[rule_id] = now_time
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
                    # Send recovery notification if configured
                    recovery_msg = rule_cfg.get("recovery_message")
                    if recovery_msg and self.notification_service:
                        rec_rendered = _format_template_string(str(recovery_msg), ctx)
                        from services.notifications.models import NotificationChannel, NotificationPayload
                        rec_payload = NotificationPayload(
                            title=f"✅ Recuperación: {rule_id}",
                            message=rec_rendered,
                            channel=NotificationChannel.ALL,
                            metadata=ctx,
                        )
                        try:
                            await self.notification_service.send(rec_payload, template_context=ctx)
                        except Exception as e:
                            self._logger.warning(f"Error dispatching recovery notification for rule '{rule_id}': {e}")
                else:
                    if self.log_rule_evaluations:
                        self._logger.debug(
                            f"Rule '{rule_id}' [NO MATCH]: {target_dev}.{prop} ({actual_val}) {op} {target_val}"
                        )

    async def _execute_actions(
        self,
        rule_id: str,
        actions: list,
        context: Optional[Dict[str, Any]] = None,
        skip_notifications: bool = False,
    ) -> bool:
        """Execute configured actuator or notification actions. Returns True if all actions succeeded."""
        all_succeeded = True

        for action in actions:
            act_type = action.get("type")
            is_notification = act_type == "notification" or "channel" in action

            # Notification action handling
            if is_notification:
                if skip_notifications:
                    if self.log_rule_evaluations:
                        self._logger.info(f"Rule '{rule_id}' notification skipped (cooldown active).")
                    continue
                if not self.notification_service:
                    self._logger.warning(
                        f"Rule '{rule_id}' has notification action, but NotificationService is not attached."
                    )
                    continue

                title_raw = action.get("title") or f"Alerta de Regla: {rule_id}"
                msg_raw = action.get("message") or f"Condición de regla '{rule_id}' cumplida."
                c = context or {}
                rendered_title = _format_template_string(title_raw, c)
                rendered_msg = _format_template_string(msg_raw, c)

                from services.notifications.models import NotificationChannel, NotificationPayload
                ch_str = str(action.get("channel", "all")).lower()
                ch_enum = (
                    NotificationChannel(ch_str)
                    if ch_str in [x.value for x in NotificationChannel]
                    else NotificationChannel.ALL
                )
                webhook_id = action.get("webhook_id")

                payload = NotificationPayload(
                    title=rendered_title,
                    message=rendered_msg,
                    channel=ch_enum,
                    webhook_id=webhook_id,
                    metadata=c,
                )
                try:
                    results = await self.notification_service.send(payload, template_context=c)
                    await self.event_bus.publish(
                        topic="rule.notification_sent",
                        sender=rule_id,
                        payload={"rule_id": rule_id, "action": action, "results": [r.model_dump() for r in results]},
                    )
                except Exception as e:
                    self._logger.error(f"Error sending notification for rule '{rule_id}': {e}")
                    all_succeeded = False
                continue

            # Actuator action handling
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
