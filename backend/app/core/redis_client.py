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
    """

    def __init__(self, cooldown_seconds: float = 30.0) -> None:
        self.cooldown_seconds = cooldown_seconds
        self._down_until = 0.0

    @property
    def is_open(self) -> bool:
        return time.monotonic() < self._down_until

    def trip(self) -> None:
        self._down_until = time.monotonic() + self.cooldown_seconds


redis_breaker = RedisBreaker()


async def get_redis():
    """Dependency injection for Redis client."""
    yield redis_client
