"""WebRTC signalling for live interviews.

The two browsers (candidate and interviewer) exchange SDP offers/answers and
ICE candidates through this socket; media then flows peer-to-peer. Messages
are JSON objects with a ``type`` (``offer``, ``answer``, ``ice``, ``hangup``)
and are relayed verbatim to the other participant.

Rooms are shared through Redis (``app/services/interview_hub.py``), so the two participants may
be connected to different backend processes; without Redis they must share one process.
"""

import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.api.monitoring import _authenticate_ws
from app.core.database import async_session_maker
from app.core.logging import logger
from app.models.interview import InterviewSession
from app.models.session import ExamSession
from app.models.user import UserRole
from app.services.interview_hub import hub, send_json

router = APIRouter(prefix="/ws", tags=["Interview signalling"])

_STAFF = {UserRole.ADMIN, UserRole.PROCTOR, UserRole.REVIEWER}
_RELAYED = {"offer", "answer", "ice", "hangup"}
_MAX_MESSAGE_BYTES = 64 * 1024


@router.websocket("/interview/{interview_id}")
async def interview_signalling(websocket: WebSocket, interview_id: str) -> None:
    await websocket.accept()
    user = await _authenticate_ws(websocket, roles=_STAFF | {UserRole.CANDIDATE})
    if user is None:
        return
    try:
        iid = uuid.UUID(interview_id)
    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid interview id")
        return

    async with async_session_maker() as db:
        interview = await db.get(InterviewSession, iid)
        session = await db.get(ExamSession, interview.exam_session_id) if interview else None
    if interview is None or session is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Interview not found")
        return
    if user.role == UserRole.CANDIDATE:
        if session.candidate_id != user.id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Not your interview")
            return
        if not interview.recording_consent:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Consent required")
            return
        seat = "candidate"
    else:
        seat = "interviewer"
    if interview.status == "COMPLETED":
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Interview has ended")
        return

    conn = await hub.join(interview_id, seat, websocket)

    # Tell both sides who is present; the interviewer creates the offer.
    await send_json(websocket, {"type": "joined", "seat": seat, "peer_present": conn.peer_present})
    await hub.relay(conn, {"type": "peer-joined", "seat": seat})

    try:
        while True:
            raw = await websocket.receive_text()
            if len(raw) > _MAX_MESSAGE_BYTES:
                continue
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if message.get("type") == "ping":
                await send_json(websocket, {"type": "pong"})
            elif message.get("type") in _RELAYED and hub.holds_seat(conn):
                await hub.relay(conn, message)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("interview_ws.error", interview_id=interview_id, error=str(exc))
    finally:
        if await hub.leave(conn):
            await hub.relay(conn, {"type": "peer-left", "seat": seat})
