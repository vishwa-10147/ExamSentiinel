"""Resilience under load: the Redis circuit breaker (one probe at a time) and the pooled engine client.

Regression test for a burst stall: with Redis down, every request in a burst tried to
connect at once, and redis-py connects under a pool lock, so 100 sign-ins took 51 s.
"""

from app.core import redis_client
from app.core.redis_client import RedisBreaker


def _clock(monkeypatch, start: float = 1000.0):
    now = [start]
    monkeypatch.setattr(redis_client.time, "monotonic", lambda: now[0])
    return now


def test_only_one_caller_probes_at_startup(monkeypatch):
    now = _clock(monkeypatch)
    breaker = RedisBreaker(cooldown_seconds=30, probe_seconds=3)
    assert breaker.is_open is False, "the first caller probes Redis"
    assert all(breaker.is_open for _ in range(100)), "everyone else uses the fallback meanwhile"
    now[0] += 3.1  # the probe reported no failure: Redis is up
    assert breaker.is_open is False and breaker.is_open is False


def test_failed_probe_opens_for_the_cooldown_then_probes_again(monkeypatch):
    now = _clock(monkeypatch)
    breaker = RedisBreaker(cooldown_seconds=30, probe_seconds=3)
    assert breaker.is_open is False
    breaker.trip()  # the probe failed
    assert breaker.is_open is True
    now[0] += 29
    assert breaker.is_open is True
    now[0] += 2  # cool-down over: exactly one new probe
    assert breaker.is_open is False
    assert breaker.is_open is True


def test_a_healthy_redis_stays_closed(monkeypatch):
    now = _clock(monkeypatch)
    breaker = RedisBreaker(cooldown_seconds=30, probe_seconds=3)
    breaker.is_open  # startup probe
    now[0] += 5
    assert not any(breaker.is_open for _ in range(1000))


async def test_sandbox_reuses_one_pooled_http_client():
    """A new HTTP client (and connection) per engine call cost 150-400 ms and capped judging at
    ~6 verdicts/s; the service must reuse one keep-alive client within an event loop."""
    from app.services.sandbox_service import SandboxService

    service = SandboxService()
    first = service._http()
    assert service._http() is first
    assert not first.is_closed
    await first.aclose()
    assert service._http() is not first, "a closed client is replaced"


def test_a_successful_call_ends_the_probe_early(monkeypatch):
    _clock(monkeypatch)
    breaker = RedisBreaker(cooldown_seconds=30, probe_seconds=3)
    assert breaker.is_open is False  # this caller probes
    assert breaker.is_open is True  # others wait for the outcome...
    breaker.succeeded()  # ...which arrives at once
    assert breaker.is_open is False
    breaker.trip()
    breaker.succeeded()  # a stale success during the cool-down changes nothing
    assert breaker.is_open is True


def test_the_api_never_imports_the_problem_bank():
    """Importing practice_bank builds the whole bank (~6 s of CPU in production). Done inside a
    request it froze every request of that API process on its first progress page."""
    import subprocess
    import sys

    code = "import sys, app.main; print('practice_bank' in sys.modules)"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
    assert result.stdout.strip().splitlines()[-1] == "False", result.stderr[-2000:]


async def test_a_saturated_database_answers_503_with_retry_after(async_client, seed_users, monkeypatch):
    """PostgreSQL out of connections (or the pool wait timing out) is "busy, retry", not a 500."""
    from sqlalchemy.exc import DBAPIError, TimeoutError as PoolTimeout

    from app.api import practice
    from app.models.user import UserRole
    from tests.test_exam_engine import auth_header

    headers = auth_header(next(u for u in seed_users if u.role == UserRole.CANDIDATE))
    failures = [
        DBAPIError("SELECT 1", {}, Exception("sorry, too many clients already")),
        PoolTimeout("QueuePool limit of size 5 overflow 5 reached, connection timed out"),
    ]
    for failure in failures:
        async def broken(*args, **kwargs):
            raise failure

        monkeypatch.setattr(practice, "_topic_progress", broken)
        r = await async_client.get("/api/practice/topics", headers=headers)
        assert r.status_code == 503 and r.headers["retry-after"] == "5", r.text
        assert "busy" in r.json()["detail"]

    async def bug(*args, **kwargs):
        raise ValueError("an ordinary bug")

    monkeypatch.setattr(practice, "_topic_progress", bug)
    assert (await async_client.get("/api/practice/topics", headers=headers)).status_code == 500
