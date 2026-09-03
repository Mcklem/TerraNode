import asyncio
import datetime
import time
from typing import Any, Dict, List, Optional
from core.device_manager import DeviceManager
from core.event_bus import EventBus
from services.live_command.command_dispatcher import CommandDispatcher
from services.live_command.models import CommandSource, LiveCommandRequest
from utils.logging import get_logger


def match_cron_field(field_str: str, val: int) -> bool:
    """Evaluate a single 5-field cron pattern against an integer time value."""
    if field_str == "*":
        return True
    if "," in field_str:
        return any(match_cron_field(part.strip(), val) for part in field_str.split(","))
    if field_str.startswith("*/"):
        try:
            step = int(field_str[2:])
            return val % step == 0
        except ValueError:
            return False
    if "-" in field_str:
        try:
            low, high = map(int, field_str.split("-"))
            return low <= val <= high
        except ValueError:
            return False
    try:
        return int(field_str) == val
    except ValueError:
        return False


def match_cron(cron_str: str, dt: datetime.datetime) -> bool:
    """Evaluate a 5-field cron string (minute, hour, day, month, day_of_week) against datetime."""
    parts = cron_str.strip().split()
    if len(parts) != 5:
        return False

    min_part, hour_part, dom_part, month_part, dow_part = parts

    # Cron weekday: 0=Sunday, 1=Monday... 6=Saturday or 7=Sunday
    # Python weekday(): 0=Monday... 6=Sunday
    py_dow = dt.weekday()
    cron_dow = (py_dow + 1) % 7

    match_min = match_cron_field(min_part, dt.minute)
    match_hour = match_cron_field(hour_part, dt.hour)
    match_dom = match_cron_field(dom_part, dt.day)
    match_month = match_cron_field(month_part, dt.month)
    match_dow = match_cron_field(dow_part, cron_dow) or match_cron_field(dow_part, py_dow)

    return match_min and match_hour and match_dom and match_month and match_dow


class TimeScheduler:
    """Time-based and Calendar Actuator Scheduler supporting intervals, duration timers, daily schedules, and cron expressions."""

    def __init__(
        self,
        schedules_config: Dict[str, dict],
        device_manager: DeviceManager,
        event_bus: EventBus,
        command_dispatcher: CommandDispatcher,
    ):
        self.schedules_config = schedules_config
        self.device_manager = device_manager
        self.event_bus = event_bus
        self.command_dispatcher = command_dispatcher
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._active_duration_tasks: Dict[str, asyncio.Task] = {}
        self._last_runs: Dict[str, float] = {}
        self._last_minute_fired: Dict[str, str] = {}  # schedule_id -> "YYYY-MM-DD HH:MM"
        self._logger = get_logger("TimeScheduler")

    def start(self) -> None:
        """Start the background time evaluation loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        self._logger.info(
            f"TimeScheduler started with {len(self.schedules_config)} schedule task(s) configured."
        )

    def stop(self) -> None:
        """Stop scheduler loop and cancel active duration timers."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

        for sched_id, task in list(self._active_duration_tasks.items()):
            if not task.done():
                task.cancel()
        self._active_duration_tasks.clear()
        self._logger.info("TimeScheduler stopped.")

    async def _loop(self) -> None:
        """Main periodic loop evaluating schedule conditions every second."""
        while self._running:
            try:
                await self._evaluate_schedules()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Error in TimeScheduler loop: {e}", exc_info=True)

            try:
                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                break

    async def _evaluate_schedules(self) -> None:
        """Evaluate all enabled schedules against current datetime and interval timers."""
        now_dt = datetime.datetime.now()
        now_ts = time.time()
        now_minute_str = now_dt.strftime("%Y-%m-%d %H:%M")

        for sched_id, cfg in self.schedules_config.items():
            if not cfg.get("enabled", True):
                continue

            should_trigger = False

            # 1. Interval-based trigger
            interval = cfg.get("interval")
            if interval:
                last_run = self._last_runs.get(sched_id, 0.0)
                if last_run == 0.0:
                    run_on_start = cfg.get("run_on_start", cfg.get("trigger_on_start", False))
                    if run_on_start:
                        should_trigger = True
                    else:
                        self._last_runs[sched_id] = now_ts
                elif now_ts - last_run >= interval:
                    should_trigger = True

            # 2. Daily Time-of-day trigger (e.g. "08:00")
            target_time = cfg.get("time")
            if target_time:
                current_time_str = now_dt.strftime("%H:%M")
                if current_time_str == target_time:
                    # Check day of week if specified
                    days = cfg.get("days")
                    current_day_str = now_dt.strftime("%a").lower()[:3]
                    if not days or any(d.lower()[:3] == current_day_str for d in days):
                        if self._last_minute_fired.get(sched_id) != now_minute_str:
                            should_trigger = True

            # 3. Cron expression trigger (e.g. "0 8 * * *")
            cron_expr = cfg.get("cron")
            if cron_expr:
                if match_cron(cron_expr, now_dt):
                    if self._last_minute_fired.get(sched_id) != now_minute_str:
                        should_trigger = True

            if should_trigger:
                self._last_minute_fired[sched_id] = now_minute_str
                self._last_runs[sched_id] = now_ts
                await self.trigger_schedule(sched_id)

    async def trigger_schedule(self, schedule_id: str) -> bool:
        """Trigger execution of a scheduled task by ID."""
        cfg = self.schedules_config.get(schedule_id)
        if not cfg:
            self._logger.warning(f"Schedule '{schedule_id}' not found in configuration.")
            return False

        device_id = cfg.get("device")
        command = cfg.get("command")
        args = cfg.get("args", {})
        stop_command = cfg.get("stop_command")
        stop_args = cfg.get("stop_args", {})
        duration = cfg.get("duration", 0)

        if not device_id or not command:
            self._logger.warning(f"Schedule '{schedule_id}' missing device or command.")
            return False

        self._logger.info(
            f"Schedule '{schedule_id}' [TRIGGER]: Executing '{command}' on device '{device_id}'"
        )

        req = LiveCommandRequest(
            device_id=device_id,
            action=command,
            params=args,
            source=CommandSource.SCHEDULER,
            user_id=f"schedule:{schedule_id}",
        )
        res = await self.command_dispatcher.dispatch(req)

        if res.success:
            await self.event_bus.publish(
                topic="schedule.triggered",
                sender=schedule_id,
                payload={
                    "schedule_id": schedule_id,
                    "device_id": device_id,
                    "action": command,
                    "duration": duration,
                    "status": "SUCCESS",
                    "success": True,
                },
            )

            # If duration is set and stop_command is specified, handle duration timer
            if duration > 0 and stop_command:
                # Cancel existing duration task for this schedule if active
                if schedule_id in self._active_duration_tasks:
                    existing_task = self._active_duration_tasks[schedule_id]
                    if not existing_task.done():
                        existing_task.cancel()

                dur_task = asyncio.create_task(
                    self._duration_timer(schedule_id, device_id, stop_command, stop_args, duration)
                )
                self._active_duration_tasks[schedule_id] = dur_task

            return True
        else:
            self._logger.info(
                f"Schedule '{schedule_id}' action on '{device_id}' blocked by dispatcher: {res.message}"
            )
            await self.event_bus.publish(
                topic="schedule.triggered",
                sender=schedule_id,
                payload={
                    "schedule_id": schedule_id,
                    "device_id": device_id,
                    "action": command,
                    "duration": duration,
                    "status": "BLOCKED",
                    "success": False,
                    "message": res.message,
                },
            )
            return False

    async def _duration_timer(
        self, schedule_id: str, device_id: str, stop_command: str, stop_args: dict, duration: float
    ) -> None:
        """Background duration timer that executes stop_command after duration seconds."""
        try:
            self._logger.info(
                f"Schedule '{schedule_id}' [DURATION TIMER]: Active for {duration}s on '{device_id}'"
            )
            await asyncio.sleep(duration)

            self._logger.info(
                f"Schedule '{schedule_id}' [DURATION EXPIRED]: Executing '{stop_command}' on '{device_id}'"
            )
            req = LiveCommandRequest(
                device_id=device_id,
                action=stop_command,
                params=stop_args,
                source=CommandSource.SCHEDULER,
                user_id=f"schedule:{schedule_id}:stop",
            )
            res = await self.command_dispatcher.dispatch(req)

            await self.event_bus.publish(
                topic="schedule.completed",
                sender=schedule_id,
                payload={
                    "schedule_id": schedule_id,
                    "device_id": device_id,
                    "stop_action": stop_command,
                    "duration": duration,
                    "status": "SUCCESS" if res.success else "BLOCKED",
                    "success": res.success,
                },
            )
        except asyncio.CancelledError:
            self._logger.debug(f"Schedule '{schedule_id}' duration timer cancelled.")
        except Exception as e:
            self._logger.error(f"Error in duration timer for schedule '{schedule_id}': {e}")
        finally:
            self._active_duration_tasks.pop(schedule_id, None)

    def get_schedule_states(self) -> List[Dict[str, Any]]:
        """Return human-readable status reports for all schedules."""
        result = []
        now_ts = time.time()
        for sched_id, cfg in self.schedules_config.items():
            last_run = self._last_runs.get(sched_id)
            duration_task = self._active_duration_tasks.get(sched_id)
            is_duration_active = duration_task is not None and not duration_task.done()

            result.append({
                "id": sched_id,
                "enabled": cfg.get("enabled", True),
                "device": cfg.get("device"),
                "command": cfg.get("command"),
                "args": cfg.get("args", {}),
                "stop_command": cfg.get("stop_command"),
                "stop_args": cfg.get("stop_args", {}),
                "duration_seconds": cfg.get("duration", 0),
                "is_duration_active": is_duration_active,
                "run_on_start": cfg.get("run_on_start", cfg.get("trigger_on_start", False)),
                "time": cfg.get("time"),
                "interval": cfg.get("interval"),
                "cron": cfg.get("cron"),
                "days": cfg.get("days"),
                "last_run_timestamp": last_run,
            })
        return result
