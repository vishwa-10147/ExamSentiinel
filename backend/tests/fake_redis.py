"""In-memory stand-in for the redis-py asyncio calls used by cross-process features.

Only what those features use: SET (nx/ex/get), GET, EXISTS, EVAL of the two owner-token
scripts, PUBLISH and pub/sub with ``get_message(timeout=...)`` (which, like redis-py, returns
None when idle). Several "processes" share one instance in a test. Expiry is not simulated.
"""

import asyncio
from collections import defaultdict

from app.core.redis_client import COMPARE_AND_DELETE, COMPARE_AND_EXPIRE


class FakeRedis:
    def __init__(self) -> None:
        self.kv: dict[str, str] = {}
        self.ttl: dict[str, int] = {}
        self.subscribers: dict[str, list["FakePubSub"]] = defaultdict(list)
        self.published: list[tuple[str, str]] = []

    async def set(self, key, value, ex=None, nx=False, get=False):
        previous = self.kv.get(key)
        if nx and previous is not None:
            return None
        self.kv[key] = value
        if ex:
            self.ttl[key] = ex
        return previous if get else True

    async def get(self, key):
        return self.kv.get(key)

    async def exists(self, *keys):
        return sum(1 for k in keys if k in self.kv)

    async def eval(self, script, numkeys, *args):
        key, token = args[0], args[1]
        if self.kv.get(key) != token:
            return 0
        if script == COMPARE_AND_DELETE:
            del self.kv[key]
            return 1
        if script == COMPARE_AND_EXPIRE:
            self.ttl[key] = int(args[2])
            return 1
        raise NotImplementedError(script)

    async def publish(self, channel, message):
        self.published.append((channel, message))
        for sub in list(self.subscribers[channel]):
            sub.queue.put_nowait({"type": "message", "channel": channel, "data": message})
        return len(self.subscribers[channel])

    def pubsub(self):
        return FakePubSub(self)


class FakePubSub:
    def __init__(self, redis: FakeRedis) -> None:
        self.redis = redis
        self.queue: asyncio.Queue = asyncio.Queue()
        self.channels: list[str] = []

    async def subscribe(self, *channels):
        for channel in channels:
            self.redis.subscribers[channel].append(self)
            self.channels.append(channel)

    async def get_message(self, ignore_subscribe_messages=False, timeout=0.0):
        try:
            return await asyncio.wait_for(self.queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    async def aclose(self):
        for channel in self.channels:
            if self in self.redis.subscribers[channel]:
                self.redis.subscribers[channel].remove(self)
        self.channels = []


class Breaker:
    """Stand-in for RedisBreaker with a fixed state."""

    def __init__(self, is_open: bool = False) -> None:
        self.is_open = is_open
        self.trips = 0

    def trip(self) -> None:
        self.trips += 1

    def succeeded(self) -> None:
        pass
