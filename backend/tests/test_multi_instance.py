"""Features that must work when the API runs as several processes sharing one Redis:
interview signalling, live monitoring events and the one-run-per-user guard. Two hub/manager
objects sharing a fake Redis stand in for two processes; see tests/fake_redis.py."""

import asyncio
import json
import uuid

import pytest
from fastapi import HTTPException
from fastapi.websockets import WebSocketState

from app.core.user_slots import UserSlot
from app.services.interview_hub import InterviewHub
from app.websocket.manager import ConnectionManager
from tests.fake_redis import Breaker, FakeRedis


class FakeSocket:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.closed = False
        self.application_state = WebSocketState.CONNECTED

    async def accept(self):
        pass

    async def send_text(self, text):
        if self.closed:
            raise RuntimeError("closed")
        self.sent.append(json.loads(text))

    async def send_json(self, message):
        await self.send_text(json.dumps(message))

    async def close(self, *args, **kwargs):
        self.closed = True
        self.application_state = WebSocketState.DISCONNECTED

    def types(self) -> list[str]:
        return [m.get("type") for m in self.sent]


async def eventually(check, timeout: float = 3.0):
    deadline = asyncio.get_running_loop().time() + timeout
    while not check():
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError("condition not met in time")
        await asyncio.sleep(0.02)


# ---------------------------------------------------------------------------
# Interview signalling
# ---------------------------------------------------------------------------

async def test_interview_participants_on_different_processes_reach_each_other():
    redis = FakeRedis()
    a, b = InterviewHub(redis, Breaker()), InterviewHub(redis, Breaker())
    iid = str(uuid.uuid4())

    cand_ws, int_ws = FakeSocket(), FakeSocket()
    cand = await a.join(iid, "candidate", cand_ws)
    assert cand.peer_present is False
    inter = await b.join(iid, "interviewer", int_ws)
    assert inter.peer_present is True  # seen through Redis

    await b.relay(inter, {"type": "peer-joined", "seat": "interviewer"})
    await b.relay(inter, {"type": "offer", "sdp": "v=0"})
    await eventually(lambda: cand_ws.types() == ["peer-joined", "offer"])
    assert cand_ws.sent[1]["sdp"] == "v=0"

    await a.relay(cand, {"type": "answer", "sdp": "v=1"})
    await eventually(lambda: int_ws.types() == ["answer"])

    # The interviewer leaves: the candidate on the other process is told.
    assert await b.leave(inter) is True
    await b.relay(inter, {"type": "peer-left", "seat": "interviewer"})
    await eventually(lambda: cand_ws.types()[-1] == "peer-left")
    assert f"iv:{iid}:seat:interviewer" not in redis.kv
    await a.leave(cand)
    assert redis.kv == {}


async def test_rejoining_on_another_process_replaces_the_old_socket():
    redis = FakeRedis()
    a, b = InterviewHub(redis, Breaker()), InterviewHub(redis, Breaker())
    iid = str(uuid.uuid4())
    inter_ws = FakeSocket()
    inter = await a.join(iid, "interviewer", inter_ws)
    old_ws, new_ws = FakeSocket(), FakeSocket()
    old = await a.join(iid, "candidate", old_ws)

    new = await b.join(iid, "candidate", new_ws)  # e.g. a reconnect routed to another process
    await eventually(lambda: old_ws.closed)
    assert old_ws.types()[-1] == "replaced"
    # The replaced socket's cleanup must not announce the candidate as gone.
    assert await a.leave(old) is False

    await a.relay(inter, {"type": "offer", "sdp": "x"})
    await eventually(lambda: new_ws.types() == ["offer"])
    assert "offer" not in old_ws.types()
    await b.leave(new)
    await a.leave(inter)


async def test_same_process_replacement_and_local_delivery():
    redis = FakeRedis()
    hub = InterviewHub(redis, Breaker())
    iid = str(uuid.uuid4())
    first, second, peer = FakeSocket(), FakeSocket(), FakeSocket()
    c1 = await hub.join(iid, "candidate", first)
    c2 = await hub.join(iid, "candidate", second)
    assert first.closed and first.types() == ["replaced"]
    assert redis.published == []  # nothing to tell other processes
    i = await hub.join(iid, "interviewer", peer)
    assert i.peer_present
    await hub.relay(i, {"type": "ice", "candidate": "c"})
    assert second.types() == ["ice"]  # same process: delivered directly
    assert await hub.leave(c1) is False and await hub.leave(c2) is True
    await hub.leave(i)


async def test_interviews_work_in_one_process_without_redis():
    hub = InterviewHub(FakeRedis(), Breaker(is_open=True))
    iid = str(uuid.uuid4())
    cand_ws, int_ws = FakeSocket(), FakeSocket()
    cand = await hub.join(iid, "candidate", cand_ws)
    inter = await hub.join(iid, "interviewer", int_ws)
    assert inter.peer_present and not inter.shared
    await hub.relay(inter, {"type": "offer"})
    assert cand_ws.types() == ["offer"]
    assert await hub.leave(inter) is True
    await hub.leave(cand)


# ---------------------------------------------------------------------------
# Live monitoring events
# ---------------------------------------------------------------------------

async def test_monitoring_events_reach_dashboards_on_every_process_once():
    redis = FakeRedis()
    a = ConnectionManager(redis, Breaker(), instance_id="proc-a")
    b = ConnectionManager(redis, Breaker(), instance_id="proc-b")
    dash_a, dash_b = FakeSocket(), FakeSocket()
    await a.connect_dashboard(dash_a)
    await b.connect_dashboard(dash_b)
    await eventually(lambda: len(redis.subscribers[ConnectionManager.channel_name]) == 2)

    # A telemetry request handled by process B.
    await b.broadcast_event("s1", "e1", {"event_type": "TAB_SWITCH"})
    await eventually(lambda: len(dash_a.sent) == 1)
    await asyncio.sleep(0.2)
    assert len(dash_b.sent) == 1  # delivered locally, its own Redis echo ignored
    assert dash_a.sent[0]["data"]["event_type"] == "TAB_SWITCH" and "_origin" not in dash_a.sent[0]

    for m in (a, b):
        m.listener_task.cancel()


async def test_monitoring_listener_survives_idle_periods():
    redis = FakeRedis()
    a = ConnectionManager(redis, Breaker(), instance_id="proc-a")
    b = ConnectionManager(redis, Breaker(), instance_id="proc-b")
    dash = FakeSocket()
    await a.connect_dashboard(dash)
    await asyncio.sleep(2.5)  # longer than the old 2 s socket timeout that killed listen()
    assert not a.listener_task.done()
    await b.broadcast_risk_update("s1", "e1", {"risk_level": "MEDIUM"})
    await eventually(lambda: dash.types() == ["risk_update"])
    a.listener_task.cancel()


async def test_monitoring_without_redis_still_reaches_local_dashboards():
    m = ConnectionManager(FakeRedis(), Breaker(is_open=True), instance_id="solo")
    dash, exam_view = FakeSocket(), FakeSocket()
    await m.connect_dashboard(dash)
    await m.connect_exam(exam_view, "e1")
    await m.broadcast_session_update("e1", {"session_id": "s1", "status": "SUBMITTED"})
    assert dash.types() == ["session_update"] and exam_view.types() == ["session_update"]
    m.listener_task.cancel()


# ---------------------------------------------------------------------------
# One run per user
# ---------------------------------------------------------------------------

async def test_one_run_per_user_across_processes():
    redis, user = FakeRedis(), uuid.uuid4()
    async with UserSlot("practice", user, redis, Breaker()):
        with pytest.raises(HTTPException) as busy:
            async with UserSlot("practice", user, redis, Breaker()):  # same user, another process
                pass
        assert busy.value.status_code == 429
        async with UserSlot("practice", uuid.uuid4(), redis, Breaker()):  # other users unaffected
            pass
        async with UserSlot("playground", user, redis, Breaker()):  # separate scope
            pass
    assert redis.kv == {}  # released
    async with UserSlot("practice", user, redis, Breaker()):
        pass


async def test_a_slot_is_only_released_by_its_owner():
    redis, user = FakeRedis(), uuid.uuid4()
    first = UserSlot("practice", user, redis, Breaker())
    await first.__aenter__()
    # Simulate expiry of a stuck run and a new run taking the slot.
    redis.kv.clear()
    second = UserSlot("practice", user, redis, Breaker())
    await second.__aenter__()
    await first.__aexit__(None, None, None)
    assert redis.kv[second.key] == second.token  # the late release did not free the new run
    await second.__aexit__(None, None, None)


async def test_slot_falls_back_to_the_process_without_redis():
    user = uuid.uuid4()
    async with UserSlot("practice", user, FakeRedis(), Breaker(is_open=True)):
        with pytest.raises(HTTPException):
            async with UserSlot("practice", user, FakeRedis(), Breaker(is_open=True)):
                pass
    async with UserSlot("practice", user, FakeRedis(), Breaker(is_open=True)):
        pass


async def test_a_seat_joined_while_redis_was_unavailable_is_shared_once_redis_answers():
    """E.g. a socket that connects while the breaker is still probing Redis after startup."""
    redis = FakeRedis()
    probing = Breaker(is_open=True)
    a, b = InterviewHub(redis, probing), InterviewHub(redis, Breaker())
    iid = str(uuid.uuid4())
    int_ws, cand_ws = FakeSocket(), FakeSocket()
    inter = await a.join(iid, "interviewer", int_ws)
    assert not inter.shared and not inter.peer_present
    cand = await b.join(iid, "candidate", cand_ws)
    assert not cand.peer_present  # the interviewer is not visible yet

    probing.is_open = False  # Redis answers
    await eventually(lambda: inter.shared)
    # Both sides are told about each other, so the interviewer starts the call.
    await eventually(lambda: "peer-joined" in cand_ws.types() and "peer-joined" in int_ws.types())
    await b.relay(cand, {"type": "answer"})
    await eventually(lambda: "answer" in int_ws.types())
    assert await a.leave(inter) is True
    await b.leave(cand)
    assert redis.kv == {}
