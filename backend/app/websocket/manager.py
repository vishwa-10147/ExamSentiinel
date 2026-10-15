"""Live monitoring WebSockets (proctor dashboards) across any number of API processes.

An event is delivered straight to this process's own sockets and published to Redis tagged
with this process's ``INSTANCE_ID``; every other process's listener forwards it to its sockets
and ignores its own echoes. Without Redis, events still reach this process's sockets, which is
all a single-process deployment needs.
"""

import asyncio
import json
from typing import Dict, Optional, Set
from datetime import datetime, timezone
from fastapi import WebSocket
from fastapi.websockets import WebSocketState

from app.core.logging import logger
from app.core.redis_client import INSTANCE_ID, PUBSUB_POLL_SECONDS, redis_breaker, redis_client


class ConnectionManager:
    """Manages WebSocket connections and broadcasts events globally via Redis Pub/Sub."""

    channel_name = "examsentinel_live_events"

    def __init__(self, redis=None, breaker=None, instance_id: str = INSTANCE_ID):
        self._exam_connections: Dict[str, Set[WebSocket]] = {}
        self._session_connections: Dict[str, Set[WebSocket]] = {}
        self._dashboard_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._redis = redis or redis_client
        self._breaker = breaker or redis_breaker
        self.instance_id = instance_id
        self.listener_task: Optional[asyncio.Task] = None

    # ------------------------------------------------------------------
    # Redis listener
    # ------------------------------------------------------------------

    def _ensure_listener(self) -> None:
        loop = asyncio.get_running_loop()
        task = self.listener_task
        if task is None or task.done() or task.get_loop() is not loop:
            self.listener_task = loop.create_task(self._listen())

    async def _listen(self) -> None:
        """Forward other processes' events to local sockets; reconnect after Redis outages."""
        while True:
            if self._breaker.is_open:
                await asyncio.sleep(PUBSUB_POLL_SECONDS)
                continue
            pubsub = self._redis.pubsub()
            try:
                await pubsub.subscribe(self.channel_name)
                self._breaker.succeeded()
                logger.info("live_events.listener_subscribed", instance=self.instance_id)
                while True:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=PUBSUB_POLL_SECONDS)
                    if message and message.get("type") == "message":
                        await self._on_message(message["data"])
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("live_events.listener_error", error=str(exc))
                self._breaker.trip()
            finally:
                try:
                    await pubsub.aclose()
                except Exception:
                    pass

    async def _on_message(self, data) -> None:
        try:
            payload = json.loads(data.decode("utf-8") if isinstance(data, bytes) else data)
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.error("live_events.bad_message")
            return
        if payload.pop("_origin", None) == self.instance_id:
            return  # already delivered locally by _publish
        await self._broadcast_to_all_tiers_local(payload.get("session_id", ""), payload.get("exam_id", ""), payload)

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect_dashboard(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._dashboard_connections.add(websocket)
        self._ensure_listener()

    async def connect_exam(self, websocket: WebSocket, exam_id: str) -> None:
        await websocket.accept()
        async with self._lock:
            self._exam_connections.setdefault(exam_id, set()).add(websocket)
        self._ensure_listener()

    async def connect_session(self, websocket: WebSocket, session_id: str) -> None:
        await websocket.accept()
        async with self._lock:
            self._session_connections.setdefault(session_id, set()).add(websocket)
        self._ensure_listener()

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._dashboard_connections.discard(websocket)
            for groups in (self._exam_connections, self._session_connections):
                for key, connections in list(groups.items()):
                    connections.discard(websocket)
                    if not connections:
                        del groups[key]

    # ------------------------------------------------------------------
    # Broadcasting
    # ------------------------------------------------------------------

    async def _publish(self, session_id: str, exam_id: str, message: dict):
        await self._broadcast_to_all_tiers_local(session_id, exam_id, message)
        if self._breaker.is_open:
            return
        try:
            await self._redis.publish(self.channel_name, json.dumps({**message, "_origin": self.instance_id}))
            self._breaker.succeeded()
        except Exception:
            self._breaker.trip()  # other processes miss this event; local sockets already have it

    async def broadcast_risk_update(self, session_id: str, exam_id: str, data: dict) -> None:
        message = {
            "type": "risk_update",
            "session_id": session_id,
            "exam_id": exam_id,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self._publish(session_id, exam_id, message)

    async def broadcast_event(self, session_id: str, exam_id: str, event_data: dict) -> None:
        message = {
            "type": "proctoring_event",
            "session_id": session_id,
            "exam_id": exam_id,
            "data": event_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self._publish(session_id, exam_id, message)

    async def broadcast_session_update(self, exam_id: str, session_data: dict) -> None:
        session_id = session_data.get("session_id", "")
        message = {
            "type": "session_update",
            "exam_id": exam_id,
            "session_id": session_id,
            "data": session_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self._publish(session_id, exam_id, message)

    # ------------------------------------------------------------------
    # Local Broadcaster
    # ------------------------------------------------------------------

    async def _broadcast_to_all_tiers_local(self, session_id: str, exam_id: str, message: dict) -> None:
        targets = set(self._dashboard_connections)
        if exam_id:
            targets |= self._exam_connections.get(exam_id, set())
        if session_id:
            targets |= self._session_connections.get(session_id, set())
        stale = [ws for ws in targets if not await self._safe_send(ws, message)]
        for ws in stale:
            await self.disconnect(ws)

    async def _safe_send(self, websocket: WebSocket, message: dict) -> bool:
        try:
            if websocket.application_state == WebSocketState.DISCONNECTED:
                return False
            await websocket.send_json(message)
            return True
        except Exception:
            return False


manager = ConnectionManager()
