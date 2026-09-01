import asyncio
import time
from typing import Dict, List, Optional
from core.device_manager import DeviceManager
from core.event_bus import EventBus
from core.settings import settings
from devices.sensor import Sensor
from utils.logging import get_logger


class Scheduler:
    """Central asyncio periodic polling scheduler for sensors."""

    def __init__(
        self,
        device_manager: DeviceManager,
        event_bus: EventBus,
        log_readings: Optional[bool] = None,
    ):
        self.device_manager = device_manager
        self.event_bus = event_bus
        self.log_readings = log_readings if log_readings is not None else settings.log_readings
        self._tasks: List[asyncio.Task] = []
        self._running: bool = False
        self._logger = get_logger("Scheduler")

    async def start(self) -> None:
        """Start polling tasks for all registered sensors."""
        if self._running:
            return

        self._running = True
        sensors = self.device_manager.get_sensors()

        for sensor in sensors:
            task = asyncio.create_task(self._poll_sensor_loop(sensor))
            self._tasks.append(task)

        self._logger.info(
            f"Scheduler started with {len(self._tasks)} sensor polling tasks (log_readings={self.log_readings})."
        )

    async def stop(self) -> None:
        """Cancel all running sensor polling tasks cleanly."""
        self._running = False
        for task in self._tasks:
            task.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks.clear()

        self._logger.info("Scheduler stopped.")

    async def _poll_sensor_loop(self, sensor: Sensor) -> None:
        """Periodic loop for reading a single sensor."""
        interval = max(1, sensor.poll_interval)
        self._logger.debug(f"Starting polling loop for sensor '{sensor.id}' every {interval}s")

        # Context-aware logger adapter for this sensor device
        dev_logger = get_logger("SensorReading", node_id=sensor.node.id, device_id=sensor.id)

        # Initial delay staggering
        await asyncio.sleep(0.1)

        while self._running:
            loop_start = time.time()
            try:
                state = await sensor.read()
                val = state.get("value")
                status = state.get("status")

                # Log measurement trace if enabled
                if self.log_readings and status == "OK" and val is not None:
                    unit = state.get("unit", "")
                    extra_parts = []
                    if "pressure" in state and state["pressure"] is not None:
                        extra_parts.append(f"Pressure: {state['pressure']} hPa")
                    if "altitude" in state and state["altitude"] is not None:
                        extra_parts.append(f"Altitude: {state['altitude']} m")

                    extra_str = f" ({', '.join(extra_parts)})" if extra_parts else ""
                    dev_logger.info(f"Measurement: {val} {unit}{extra_str}".strip())

                # Publish measurement event if read succeeded
                if status == "OK" and val is not None:
                    await self.event_bus.publish(
                        topic="device.value_changed",
                        sender=sensor.id,
                        payload=state,
                    )
                else:
                    await self.event_bus.publish(
                        topic="device.status_changed",
                        sender=sensor.id,
                        payload=state,
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                dev_logger.error(f"Error polling sensor: {e}")

            # Calculate remaining sleep duration to prevent timing drift
            elapsed = time.time() - loop_start
            sleep_duration = max(0.1, interval - elapsed)

            try:
                await asyncio.sleep(sleep_duration)
            except asyncio.CancelledError:
                break
