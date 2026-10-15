"""One code-execution job per user at a time, across every API process.

A slot is a Redis key holding an owner token (released only by its owner, and expiring on its
own if a process dies mid-run). Without Redis the slot is per process, which is exact for a
single process; the per-user rate limits still apply on top.
"""

import uuid

from fastapi import HTTPException, status

from app.core.redis_client import COMPARE_AND_DELETE, redis_breaker, redis_client

# Longer than any single run (compile 15 s + run time + engine queueing).
SLOT_TTL_SECONDS = 120


class UserSlot:
    _local: set[str] = set()

    def __init__(self, scope: str, user_id: uuid.UUID, redis=None, breaker=None) -> None:
        self.key = f"run_slot:{scope}:{user_id}"
        self.token = uuid.uuid4().hex
        self._redis = redis or redis_client
        self._breaker = breaker or redis_breaker
        self._shared = False

    async def __aenter__(self) -> "UserSlot":
        if not self._breaker.is_open:
            try:
                acquired = await self._redis.set(self.key, self.token, nx=True, ex=SLOT_TTL_SECONDS)
                self._breaker.succeeded()
                self._shared = True
                if not acquired:
                    self._busy()
                return self
            except HTTPException:
                raise
            except Exception:
                self._breaker.trip()
        if self.key in self._local:
            self._busy()
        self._local.add(self.key)
        return self

    async def __aexit__(self, *exc) -> None:
        if not self._shared:
            self._local.discard(self.key)
            return
        try:
            await self._redis.eval(COMPARE_AND_DELETE, 1, self.key, self.token)
        except Exception:
            self._breaker.trip()  # the key expires on its own

    @staticmethod
    def _busy():
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "A run is already in progress. Please wait for it to finish.")
