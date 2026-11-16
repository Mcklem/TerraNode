import asyncio
import json
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from api.dependencies import get_system
from core.event_bus import Event

router = APIRouter(prefix="/api/v1/events", tags=["Events Stream"])


@router.get(
    "/stream",
    summary="Server-Sent Events (SSE) en tiempo real",
    description="Canal de transmisión unidireccional de eventos en vivo para telemetría, estados de salud, overrides y schedules.",
)
async def event_stream(request: Request, system=Depends(get_system)):
    """Yield real-time system events over an active HTTP text/event-stream connection."""
    if system is None or not hasattr(system, "event_bus"):
        async def empty_stream():
            yield "event: connected\ndata: {}\n\n"
        return StreamingResponse(empty_stream(), media_type="text/event-stream")

    event_bus = system.event_bus
    queue: asyncio.Queue = asyncio.Queue(maxsize=200)

    def _listener(event: Event):
        try:
            queue.put_nowait({
                "topic": event.topic,
                "sender": event.sender,
                "payload": event.payload,
                "timestamp": event.timestamp,
            })
        except asyncio.QueueFull:
            pass

    event_bus.subscribe("*", _listener)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            yield f"event: connected\ndata: {json.dumps({'message': 'Connected to TerraNode SSE stream'})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    evt_data = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"event: {evt_data['topic']}\ndata: {json.dumps(evt_data)}\n\n"
                except asyncio.TimeoutError:
                    # Keepalive comment frame to maintain HTTP connection across proxies
                    yield ": keep-alive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            event_bus.unsubscribe("*", _listener)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
