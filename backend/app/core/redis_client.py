import time

import redis.asyncio as redis

from app.core.config import settings

# Global Redis connection pool. Short timeouts: every caller has a fallback,
# so a missing Redis must cost milliseconds, not seconds, per request.
redis_client = redis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
    socket_connect_timeout=0.5,
    socket_timeout=2,
)


class RedisBreaker:
    """Skip Redis for a cool-down period after a connection failure.

    Callers check ``is_open`` before touching Redis and call ``trip()`` when a
    call fails, so an outage costs one timeout per cool-down instead of one
    per request.

    After the cool-down the breaker is *half-open*: exactly one caller is let
    through to probe Redis while everyone else keeps using their fallback. If
    the probe fails it trips again; if no failure is reported within
    ``probe_seconds`` Redis is considered back. Without this, every request in
    a burst would try to connect at once - and redis-py opens connections under
    a pool lock, so a burst of N requests would wait N x the connect timeout.
    The breaker also starts half-open, because Redis may be missing at boot.
    """

    def __init__(self, cooldown_seconds: float = 30.0, probe_seconds: float = 3.0) -> None:
        self.cooldown_seconds = cooldown_seconds
        self.probe_seconds = probe_seconds
        self._down_until = 0.0
        self._recovering = True
        self._probe_until = 0.0

    @property
    def is_open(self) -> bool:
        now = time.monotonic()
        if now < self._down_until:
            return True
        if self._recovering:
            if self._probe_until == 0.0:
                self._probe_until = now + self.probe_seconds  # this caller probes Redis
                return False
            if now < self._probe_until:
                return True  # wait for the probe's outcome
            self._recovering, self._probe_until = False, 0.0  # probe passed: Redis is back
        return False

    def trip(self) -> None:
        self._down_until = time.monotonic() + self.cooldown_seconds
        self._recovering, self._probe_until = True, 0.0


redis_breaker = RedisBreaker()


async def get_redis():
    """Dependency injection for Redis client."""
    yield redis_client
