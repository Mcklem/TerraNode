import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List
from utils.logging import get_logger


@dataclass
class Event:
    topic: str
    sender: str
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)


EventHandler = Callable[[Event], Any]


class EventBus:
    """Decoupled asynchronous event bus supporting wildcard topic subscriptions."""

    def __init__(self):
        self._listeners: Dict[str, List[EventHandler]] = {}
        self._logger = get_logger("EventBus")

    def subscribe(self, topic_pattern: str, handler: EventHandler) -> None:
        """Subscribe a handler callback to an event topic pattern."""
        if topic_pattern not in self._listeners:
            self._listeners[topic_pattern] = []
        if handler not in self._listeners[topic_pattern]:
            self._listeners[topic_pattern].append(handler)
            self._logger.debug(f"Subscribed handler {handler.__name__} to topic '{topic_pattern}'")

    def unsubscribe(self, topic_pattern: str, handler: EventHandler) -> None:
        if topic_pattern in self._listeners and handler in self._listeners[topic_pattern]:
            self._listeners[topic_pattern].remove(handler)

    async def publish(self, topic: str, sender: str, payload: Dict[str, Any]) -> None:
        """Publish an event to all matching subscribed listeners."""
        event = Event(topic=topic, sender=sender, payload=payload)
        matched_handlers: List[EventHandler] = []

        for pattern, handlers in self._listeners.items():
            if self._topic_matches(pattern, topic):
                for h in handlers:
                    if h not in matched_handlers:
                        matched_handlers.append(h)

        async def _invoke_safe(handler: EventHandler):
            try:
                res = handler(event)
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:
                self._logger.error(f"Error in event handler for topic '{topic}': {e}", exc_info=True)

        if matched_handlers:
            tasks = [_invoke_safe(h) for h in matched_handlers]
            await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    def _topic_matches(pattern: str, topic: str) -> bool:
        if pattern == "*" or pattern == topic:
            return True
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            return topic.startswith(prefix + ".")
        return False
