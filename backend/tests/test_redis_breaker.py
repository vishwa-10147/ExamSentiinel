"""Redis circuit breaker: after a failure, only one caller at a time probes Redis.

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
