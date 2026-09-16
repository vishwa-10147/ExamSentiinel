"""
WebSocket connection manager for real-time exam monitoring.

Manages three tiers of connections:
- Dashboard: Global feed of all risk updates and events across all exams.
- Exam: Scoped feed for a specific exam's sessions.
- Session: Scoped feed for a single student's session.

Usage:
    from app.websocket.manager import manager
    await manager.broadcast_risk_update(session_id, exam_id, data)
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Set

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.core.logging import logger


class ConnectionManager:
    """Manages WebSocket connections for real-time exam monitoring."""

    def __init__(self) -> None:
        # Map of exam_id -> set of connected admin WebSockets
        self._exam_connections: Dict[str, Set[WebSocket]] = {}
        # Map of session_id -> set of connected admin WebSockets watching that specific session
        self._session_connections: Dict[str, Set[WebSocket]] = {}
        # All active admin connections for global dashboard
        self._dashboard_connections: Set[WebSocket] = set()
        # Lock to protect concurrent modification of connection sets
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect_dashboard(self, websocket: WebSocket) -> None:
        """Connect an admin to the global dashboard feed."""
        await websocket.accept()
        async with self._lock:
            self._dashboard_connections.add(websocket)
        logger.info(
            "dashboard_ws_connected",
            total=len(self._dashboard_connections),
        )

    async def connect_exam(self, websocket: WebSocket, exam_id: str) -> None:
        """Connect an admin to monitor a specific exam."""
        await websocket.accept()
        async with self._lock:
            if exam_id not in self._exam_connections:
                self._exam_connections[exam_id] = set()
            self._exam_connections[exam_id].add(websocket)
        logger.info(
            "exam_ws_connected",
            exam_id=exam_id,
            total=len(self._exam_connections[exam_id]),
        )

    async def connect_session(self, websocket: WebSocket, session_id: str) -> None:
        """Connect an admin to monitor a specific student session."""
        await websocket.accept()
        async with self._lock:
            if session_id not in self._session_connections:
                self._session_connections[session_id] = set()
            self._session_connections[session_id].add(websocket)
        logger.info(
            "session_ws_connected",
            session_id=session_id,
            total=len(self._session_connections[session_id]),
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket from all connection pools."""
        async with self._lock:
            # Remove from dashboard pool
            self._dashboard_connections.discard(websocket)

            # Remove from exam-scoped pools, clean up empty sets
            empty_exam_keys: list[str] = []
            for exam_id, connections in self._exam_connections.items():
                connections.discard(websocket)
                if not connections:
                    empty_exam_keys.append(exam_id)
            for key in empty_exam_keys:
                del self._exam_connections[key]

            # Remove from session-scoped pools, clean up empty sets
            empty_session_keys: list[str] = []
            for session_id, connections in self._session_connections.items():
                connections.discard(websocket)
                if not connections:
                    empty_session_keys.append(session_id)
            for key in empty_session_keys:
                del self._session_connections[key]

        logger.info("ws_disconnected")

    # ------------------------------------------------------------------
    # Broadcasting helpers
    # ------------------------------------------------------------------

    async def broadcast_risk_update(
        self, session_id: str, exam_id: str, data: dict
    ) -> None:
        """Broadcast a risk score update to all relevant listeners.

        The message is sent to:
        - All global dashboard connections
        - All connections monitoring the specific exam
        - All connections monitoring the specific session
        """
        message = {
            "type": "risk_update",
            "session_id": session_id,
            "exam_id": exam_id,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self._broadcast_to_all_tiers(session_id, exam_id, message)

    async def broadcast_event(
        self, session_id: str, exam_id: str, event_data: dict
    ) -> None:
        """Broadcast a new proctoring event to all relevant listeners."""
        message = {
            "type": "proctoring_event",
            "session_id": session_id,
            "exam_id": exam_id,
            "data": event_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self._broadcast_to_all_tiers(session_id, exam_id, message)

    async def broadcast_session_update(
        self, exam_id: str, session_data: dict
    ) -> None:
        """Broadcast session status changes (started, submitted, etc.)."""
        message = {
            "type": "session_update",
            "exam_id": exam_id,
            "data": session_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        stale: list[WebSocket] = []

        # Dashboard connections
        for ws in list(self._dashboard_connections):
            if not await self._safe_send(ws, message):
                stale.append(ws)

        # Exam-specific connections
        exam_conns = self._exam_connections.get(exam_id, set())
        for ws in list(exam_conns):
            if not await self._safe_send(ws, message):
                stale.append(ws)

        # Clean up any dead connections discovered during broadcast
        for ws in stale:
            await self.disconnect(ws)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _broadcast_to_all_tiers(
        self, session_id: str, exam_id: str, message: dict
    ) -> None:
        """Send a message to dashboard, exam-scoped, and session-scoped listeners."""
        stale: list[WebSocket] = []

        # Dashboard connections
        for ws in list(self._dashboard_connections):
            if not await self._safe_send(ws, message):
                stale.append(ws)

        # Exam-specific connections
        exam_conns = self._exam_connections.get(exam_id, set())
        for ws in list(exam_conns):
            if not await self._safe_send(ws, message):
                stale.append(ws)

        # Session-specific connections
        session_conns = self._session_connections.get(session_id, set())
        for ws in list(session_conns):
            if not await self._safe_send(ws, message):
                stale.append(ws)

        # Clean up any dead connections discovered during broadcast
        for ws in stale:
            await self.disconnect(ws)

    async def _safe_send(self, websocket: WebSocket, message: dict) -> bool:
        """Send a JSON message to a WebSocket, returning False if the connection is closed.

        Stale connections are detected so callers can remove them.
        """
        try:
            if websocket.application_state == WebSocketState.DISCONNECTED:
                return False
            await websocket.send_json(message)
            return True
        except Exception:
            logger.debug("ws_send_failed", exc_info=True)
            return False

    # ------------------------------------------------------------------
    # Diagnostic helpers
    # ------------------------------------------------------------------

    @property
    def dashboard_count(self) -> int:
        """Number of active dashboard connections."""
        return len(self._dashboard_connections)

    def exam_count(self, exam_id: str) -> int:
        """Number of active connections for a specific exam."""
        return len(self._exam_connections.get(exam_id, set()))

    def session_count(self, session_id: str) -> int:
        """Number of active connections for a specific session."""
        return len(self._session_connections.get(session_id, set()))


# Module-level singleton — import this wherever broadcasts are needed.
manager = ConnectionManager()
