import asyncio
import json
from typing import Dict, Set
from datetime import datetime, timezone
from fastapi import WebSocket
from fastapi.websockets import WebSocketState
import redis.asyncio as redis

from app.core.logging import logger
from app.core.config import settings
from app.core.redis_client import redis_client

class ConnectionManager:
    """Manages WebSocket connections and broadcasts events globally via Redis Pub/Sub."""

    def __init__(self):
        self._exam_connections: Dict[str, Set[WebSocket]] = {}
        self._session_connections: Dict[str, Set[WebSocket]] = {}
        self._dashboard_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
        
        self.pubsub = redis_client.pubsub()
        self.listener_task = None
        self.channel_name = "examsentinel_live_events"

    async def _start_listener(self):
        if not self.listener_task:
            try:
                await self.pubsub.subscribe(self.channel_name)
                self.listener_task = asyncio.create_task(self._listen_to_redis())
                logger.info("Redis PubSub listener started for WebSockets.")
            except Exception as e:
                logger.debug(f"Failed to start Redis PubSub listener (Redis might be down): {e}")

    async def _listen_to_redis(self):
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    data_str = message["data"].decode("utf-8") if isinstance(message["data"], bytes) else message["data"]
                    try:
                        payload = json.loads(data_str)
                        session_id = payload.get("session_id", "")
                        exam_id = payload.get("exam_id", "")
                        await self._broadcast_to_all_tiers_local(session_id, exam_id, payload)
                    except json.JSONDecodeError:
                        logger.error("Failed to decode Redis message")
        except Exception as e:
            logger.error(f"Redis PubSub listener error: {e}")
            self.listener_task = None

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect_dashboard(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._dashboard_connections.add(websocket)
        await self._start_listener()

    async def connect_exam(self, websocket: WebSocket, exam_id: str) -> None:
        await websocket.accept()
        async with self._lock:
            if exam_id not in self._exam_connections:
                self._exam_connections[exam_id] = set()
            self._exam_connections[exam_id].add(websocket)
        await self._start_listener()

    async def connect_session(self, websocket: WebSocket, session_id: str) -> None:
        await websocket.accept()
        async with self._lock:
            if session_id not in self._session_connections:
                self._session_connections[session_id] = set()
            self._session_connections[session_id].add(websocket)
        await self._start_listener()

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._dashboard_connections.discard(websocket)

            empty_exam_keys: list[str] = []
            for exam_id, connections in self._exam_connections.items():
                connections.discard(websocket)
                if not connections:
                    empty_exam_keys.append(exam_id)
            for key in empty_exam_keys:
                del self._exam_connections[key]

            empty_session_keys: list[str] = []
            for session_id, connections in self._session_connections.items():
                connections.discard(websocket)
                if not connections:
                    empty_session_keys.append(session_id)
            for key in empty_session_keys:
                del self._session_connections[key]

    # ------------------------------------------------------------------
    # Broadcasting
    # ------------------------------------------------------------------

    async def _publish(self, session_id: str, exam_id: str, message: dict):
        try:
            await redis_client.publish(self.channel_name, json.dumps(message))
        except Exception as e:
            # Fallback to local if Redis is down
            await self._broadcast_to_all_tiers_local(session_id, exam_id, message)

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
        stale: list[WebSocket] = []

        for ws in list(self._dashboard_connections):
            if not await self._safe_send(ws, message):
                stale.append(ws)

        if exam_id:
            exam_conns = self._exam_connections.get(exam_id, set())
            for ws in list(exam_conns):
                if not await self._safe_send(ws, message):
                    stale.append(ws)

        if session_id:
            session_conns = self._session_connections.get(session_id, set())
            for ws in list(session_conns):
                if not await self._safe_send(ws, message):
                    stale.append(ws)

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
