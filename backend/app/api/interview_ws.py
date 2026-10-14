"""WebRTC signalling for live interviews.

The two browsers (candidate and interviewer) exchange SDP offers/answers and
ICE candidates through this socket; media then flows peer-to-peer. Messages
are JSON objects with a ``type`` (``offer``, ``answer``, ``ice``, ``hangup``)
and are relayed verbatim to the other participant.

Rooms live in this process's memory, so with several backend instances the
load balancer must route both participants of an interview to the same
instance (ALB stickiness on ``/api/ws/interview/*``) — see docs/AWS_DEPLOYMENT.md.
"""

import asyncio
import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.api.monitoring import _authenticate_ws
from app.core.database import async_session_maker
from app.core.logging import logger
from app.models.interview import InterviewSession
from app.models.session import ExamSession
from app.models.user import UserRole

router = APIRouter(prefix="/ws", tags=["Interview signalling"])

_STAFF = {UserRole.ADMIN, UserRole.PROCTOR, UserRole.REVIEWER}
_RELAYED = {"offer", "answer", "ice", "hangup"}
_MAX_MESSAGE_BYTES = 64 * 1024

# interview id -> {"candidate": ws, "interviewer": ws}
_rooms: dict[str, dict[str, WebSocket]] = {}
_lock = asyncio.Lock()


async def _send(ws: WebSocket | None, message: dict) -> None:
    if ws is None:
        return
    try:
        await ws.send_text(json.dumps(message))
    except Exception:
        pass  # the peer's own loop will notice the closed socket


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
        seat, other_seat = "candidate", "interviewer"
    else:
        seat, other_seat = "interviewer", "candidate"
    if interview.status == "COMPLETED":
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Interview has ended")
        return

    async with _lock:
        room = _rooms.setdefault(interview_id, {})
        previous = room.get(seat)
        room[seat] = websocket
        peer = room.get(other_seat)
    if previous is not None:  # same seat re-joined from another tab: drop the old one
        await _send(previous, {"type": "replaced"})
        try:
            await previous.close()
        except Exception:
            pass

    # Tell both sides who is present; the interviewer creates the offer.
    await _send(websocket, {"type": "joined", "seat": seat, "peer_present": peer is not None})
    await _send(peer, {"type": "peer-joined", "seat": seat})

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
                await _send(websocket, {"type": "pong"})
            elif message.get("type") in _RELAYED:
                await _send(_rooms.get(interview_id, {}).get(other_seat), message)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("interview_ws.error", interview_id=interview_id, error=str(exc))
    finally:
        async with _lock:
            room = _rooms.get(interview_id, {})
            if room.get(seat) is websocket:
                del room[seat]
                peer = room.get(other_seat)
                if not room:
                    _rooms.pop(interview_id, None)
            else:
                peer = None  # already replaced by a newer connection
        await _send(peer, {"type": "peer-left", "seat": seat})
