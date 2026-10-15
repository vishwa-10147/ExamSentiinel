"""Interview signalling rooms that work across API processes.

Each interview has two seats, ``candidate`` and ``interviewer``. A seat is held by one
WebSocket at a time; joining a held seat replaces the older socket (another tab or a reconnect).

With Redis, a seat's holder is recorded under ``iv:{id}:seat:{seat}`` (owner token, short TTL
kept alive while connected) and messages for a seat are published on ``iv:{id}:to:{seat}``; the
process holding that seat forwards them to its socket. A peer in the same process is reached
directly. Without Redis (or while the breaker is open) rooms are process-local, which is enough
for one API process; several processes need Redis.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Optional

from fastapi import WebSocket

from app.core.logging import logger
from app.core.redis_client import (
    COMPARE_AND_DELETE,
    COMPARE_AND_EXPIRE,
    INSTANCE_ID,
    PUBSUB_POLL_SECONDS,
    redis_breaker,
    redis_client,
)

SEATS = ("candidate", "interviewer")
SEAT_TTL_SECONDS = 90
REFRESH_SECONDS = 30


def other_seat(seat: str) -> str:
    return SEATS[1] if seat == SEATS[0] else SEATS[0]


def _seat_key(interview_id: str, seat: str) -> str:
    return f"iv:{interview_id}:seat:{seat}"


def _channel(interview_id: str, seat: str) -> str:
    return f"iv:{interview_id}:to:{seat}"


@dataclass(eq=False)
class SeatConnection:
    interview_id: str
    seat: str
    websocket: WebSocket
    token: str = field(default_factory=lambda: f"{INSTANCE_ID}:{uuid.uuid4().hex}")
    shared: bool = False  # registered in Redis
    peer_present: bool = False
    task: Optional[asyncio.Task] = None


async def send_json(ws: Optional[WebSocket], message: dict) -> None:
    if ws is None:
        return
    try:
        await ws.send_text(json.dumps(message))
    except Exception:
        pass  # the peer's own loop will notice the closed socket


class InterviewHub:
    def __init__(self, redis=None, breaker=None) -> None:
        self._redis = redis or redis_client
        self._breaker = breaker or redis_breaker
        self._rooms: dict[str, dict[str, SeatConnection]] = {}
        self._lock = asyncio.Lock()

    def _redis_ok(self) -> bool:
        return not self._breaker.is_open

    # ---- membership ----------------------------------------------------------------------

    async def join(self, interview_id: str, seat: str, websocket: WebSocket) -> SeatConnection:
        conn = SeatConnection(interview_id, seat, websocket)
        async with self._lock:
            room = self._rooms.setdefault(interview_id, {})
            previous = room.get(seat)
            room[seat] = conn
            local_peer = room.get(other_seat(seat))
        if previous is not None:
            await self._evict(previous)

        remote_peer = await self._register(conn, previous) if self._redis_ok() else None
        if remote_peer is None:
            # Redis is unavailable (or the breaker is still probing): work locally for now and
            # join the shared room as soon as Redis answers.
            conn.task = asyncio.create_task(self._register_later(conn))
        conn.peer_present = local_peer is not None or bool(remote_peer)
        return conn

    async def _register(self, conn: SeatConnection, previous: Optional[SeatConnection] = None) -> Optional[bool]:
        """Publish this seat through Redis. Returns whether the other seat is held anywhere,
        or None if Redis is unavailable."""
        pubsub = None
        try:
            # Subscribe before anyone can learn about this seat, so no message is missed.
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(_channel(conn.interview_id, conn.seat))
            key = _seat_key(conn.interview_id, conn.seat)
            old = await self._redis.set(key, conn.token, ex=SEAT_TTL_SECONDS, get=True)
            if old and old != conn.token and (previous is None or old != previous.token):
                # The seat was held in another process: tell it to let go.
                await self._redis.publish(_channel(conn.interview_id, conn.seat), json.dumps({"replace": old}))
            remote_peer = bool(await self._redis.exists(_seat_key(conn.interview_id, other_seat(conn.seat))))
            self._breaker.succeeded()
        except Exception as exc:
            logger.warning("interview_hub.redis_unavailable", error=str(exc))
            self._breaker.trip()
            if pubsub is not None:
                try:
                    await pubsub.aclose()
                except Exception:
                    pass
            return None
        conn.shared = True
        conn.task = asyncio.create_task(self._listen(conn, pubsub))
        return remote_peer

    async def _register_later(self, conn: SeatConnection) -> None:
        while self.holds_seat(conn):
            if self._redis_ok():
                remote_peer = await self._register(conn)
                if remote_peer is not None:
                    logger.info("interview_hub.registered_late", interview_id=conn.interview_id, seat=conn.seat)
                    # Both sides learn about each other as if one had just joined.
                    await self.relay(conn, {"type": "peer-joined", "seat": conn.seat})
                    if remote_peer:
                        await send_json(conn.websocket, {"type": "peer-joined", "seat": other_seat(conn.seat)})
                    return
            await asyncio.sleep(PUBSUB_POLL_SECONDS)

    async def leave(self, conn: SeatConnection) -> bool:
        """Release the seat. Returns True if ``conn`` still held it (so the peer should be told)."""
        if conn.task is not None:
            conn.task.cancel()
            await asyncio.gather(conn.task, return_exceptions=True)
        async with self._lock:
            room = self._rooms.get(conn.interview_id, {})
            held = room.get(conn.seat) is conn
            if held:
                del room[conn.seat]
                if not room:
                    self._rooms.pop(conn.interview_id, None)
        if conn.shared and self._redis_ok():
            try:
                released = await self._redis.eval(COMPARE_AND_DELETE, 1, _seat_key(conn.interview_id, conn.seat), conn.token)
                held = held and bool(released)
            except Exception:
                self._breaker.trip()
        return held

    async def _evict(self, conn: SeatConnection) -> None:
        await send_json(conn.websocket, {"type": "replaced"})
        try:
            await conn.websocket.close()
        except Exception:
            pass

    # ---- messaging -----------------------------------------------------------------------

    async def send_to_seat(self, interview_id: str, seat: str, message: dict) -> None:
        local = self._rooms.get(interview_id, {}).get(seat)
        if local is not None:
            await send_json(local.websocket, message)
            return
        if self._redis_ok():
            try:
                await self._redis.publish(_channel(interview_id, seat), json.dumps({"msg": message}))
            except Exception:
                self._breaker.trip()

    async def relay(self, conn: SeatConnection, message: dict) -> None:
        await self.send_to_seat(conn.interview_id, other_seat(conn.seat), message)

    def holds_seat(self, conn: SeatConnection) -> bool:
        return self._rooms.get(conn.interview_id, {}).get(conn.seat) is conn

    async def _listen(self, conn: SeatConnection, pubsub) -> None:
        """Deliver messages published for this seat; keep the seat registration alive."""
        key = _seat_key(conn.interview_id, conn.seat)
        loop = asyncio.get_running_loop()
        next_refresh = loop.time() + REFRESH_SECONDS
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=PUBSUB_POLL_SECONDS)
                if message and message.get("type") == "message":
                    payload = json.loads(message["data"])
                    if payload.get("replace") == conn.token:
                        await self._evict(conn)
                        return
                    if "msg" in payload and self.holds_seat(conn):
                        await send_json(conn.websocket, payload["msg"])
                if loop.time() >= next_refresh:
                    next_refresh = loop.time() + REFRESH_SECONDS
                    await self._redis.eval(COMPARE_AND_EXPIRE, 1, key, conn.token, SEAT_TTL_SECONDS)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("interview_hub.listener_error", interview_id=conn.interview_id, error=str(exc))
        finally:
            try:
                await pubsub.aclose()
            except Exception:
                pass


hub = InterviewHub()
