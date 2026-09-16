"""
WebSocket endpoints for real-time exam monitoring.

Authentication is performed via a `token` query parameter because the browser
WebSocket API does not allow setting custom HTTP headers.  The token is validated
as a standard JWT access token, and only ADMIN / PROCTOR roles are permitted.
"""

import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_maker
from app.core.logging import logger
from app.core.security import decode_token
from app.models.user import User, UserRole
from app.websocket.manager import manager

router = APIRouter(prefix="/ws", tags=["WebSocket Monitoring"])

# Roles allowed to connect to monitoring WebSockets
_MONITORING_ROLES = {UserRole.ADMIN, UserRole.PROCTOR}


async def _authenticate_ws(websocket: WebSocket) -> User | None:
    """Validate the JWT token passed as a query parameter.

    Returns the authenticated User or ``None`` (after closing the socket with
    an appropriate close code) if authentication fails.
    """
    token: str | None = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing authentication token")
        return None

    # Decode and validate JWT
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token expired")
        return None
    except jwt.InvalidTokenError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
        return None

    if payload.get("type") != "access":
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token type")
        return None

    user_id_str = payload.get("user_id")
    if not user_id_str:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token payload")
        return None

    try:
        user_id = uuid.UUID(str(user_id_str))
    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Malformed user ID")
        return None

    # Fetch user from the database using a standalone session (WebSocket
    # endpoints are long-lived and cannot rely on the per-request get_db
    # dependency).
    async with async_session_maker() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user: User | None = result.scalar_one_or_none()

    if not user or not user.is_active:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found or inactive")
        return None

    if user.role not in _MONITORING_ROLES:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Insufficient permissions")
        return None

    return user


# --------------------------------------------------------------------------
# WebSocket endpoints
# --------------------------------------------------------------------------

@router.websocket("/dashboard")
async def dashboard_ws(websocket: WebSocket) -> None:
    """WebSocket endpoint for the admin dashboard.

    Receives **all** risk updates, proctoring events, and session status
    changes across every active exam.

    Connect with: ``ws://<host>/api/ws/dashboard?token=<jwt>``
    """
    user = await _authenticate_ws(websocket)
    if user is None:
        return

    await manager.connect_dashboard(websocket)
    logger.info("dashboard_ws_accepted", user_id=str(user.id), role=user.role.value)

    try:
        while True:
            # Keep the connection alive.  We listen for any client messages
            # (e.g. pings or future commands) so the await yields properly.
            data = await websocket.receive_text()
            # Echo-back heartbeat so the client can measure latency.
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        logger.info("dashboard_ws_disconnected", user_id=str(user.id))
    except Exception:
        logger.exception("dashboard_ws_error", user_id=str(user.id))
    finally:
        await manager.disconnect(websocket)


@router.websocket("/exam/{exam_id}")
async def exam_monitor_ws(websocket: WebSocket, exam_id: str) -> None:
    """WebSocket endpoint for monitoring a specific exam's sessions.

    Connect with: ``ws://<host>/api/ws/exam/<exam_id>?token=<jwt>``
    """
    user = await _authenticate_ws(websocket)
    if user is None:
        return

    await manager.connect_exam(websocket, exam_id)
    logger.info(
        "exam_ws_accepted",
        user_id=str(user.id),
        exam_id=exam_id,
        role=user.role.value,
    )

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        logger.info("exam_ws_disconnected", user_id=str(user.id), exam_id=exam_id)
    except Exception:
        logger.exception("exam_ws_error", user_id=str(user.id), exam_id=exam_id)
    finally:
        await manager.disconnect(websocket)


@router.websocket("/session/{session_id}")
async def session_monitor_ws(websocket: WebSocket, session_id: str) -> None:
    """WebSocket endpoint for monitoring a specific student session.

    Connect with: ``ws://<host>/api/ws/session/<session_id>?token=<jwt>``
    """
    user = await _authenticate_ws(websocket)
    if user is None:
        return

    await manager.connect_session(websocket, session_id)
    logger.info(
        "session_ws_accepted",
        user_id=str(user.id),
        session_id=session_id,
        role=user.role.value,
    )

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        logger.info("session_ws_disconnected", user_id=str(user.id), session_id=session_id)
    except Exception:
        logger.exception("session_ws_error", user_id=str(user.id), session_id=session_id)
    finally:
        await manager.disconnect(websocket)
