"""One-time codes (password reset) with attempt limits.

Stored in Redis when available so every backend instance sees the same code;
falls back to process memory when Redis is unreachable (fine for a single
instance / local dev — multi-instance deployments must run Redis).
"""

import hmac
import secrets
import time
from dataclasses import dataclass

from app.core.redis_client import redis_breaker, redis_client

OTP_TTL_SECONDS = 300
MAX_ATTEMPTS = 5


@dataclass
class _Entry:
    code: str
    expires_at: float
    attempts: int = 0


class OTPStore:
    def __init__(self) -> None:
        self._memory: dict[str, _Entry] = {}

    @staticmethod
    def new_code() -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    async def issue(self, purpose: str, subject: str) -> str:
        """Create (or replace) the code for ``subject`` and reset its attempt counter."""
        code = self.new_code()
        key = f"otp:{purpose}:{subject}"
        if not redis_breaker.is_open:
            try:
                async with redis_client.pipeline(transaction=True) as pipe:
                    pipe.hset(key, mapping={"code": code, "attempts": 0})
                    pipe.expire(key, OTP_TTL_SECONDS)
                    await pipe.execute()
                return code
            except Exception:
                redis_breaker.trip()
        self._memory[key] = _Entry(code, time.monotonic() + OTP_TTL_SECONDS)
        return code

    async def verify(self, purpose: str, subject: str, code: str, *, consume: bool) -> bool:
        """Check ``code``. Wrong guesses count; after MAX_ATTEMPTS the code is void."""
        key = f"otp:{purpose}:{subject}"
        if not redis_breaker.is_open:
            try:
                stored = await redis_client.hgetall(key)
                if not stored:
                    return self._verify_memory(key, code, consume)
                if int(stored.get("attempts", 0)) >= MAX_ATTEMPTS:
                    return False
                if hmac.compare_digest(stored.get("code", ""), code or ""):
                    if consume:
                        await redis_client.delete(key)
                    return True
                await redis_client.hincrby(key, "attempts", 1)
                return False
            except Exception:
                redis_breaker.trip()
        return self._verify_memory(key, code, consume)

    def _verify_memory(self, key: str, code: str, consume: bool) -> bool:
        entry = self._memory.get(key)
        if entry is None:
            return False
        if entry.expires_at < time.monotonic():
            del self._memory[key]
            return False
        if entry.attempts >= MAX_ATTEMPTS:
            return False
        if hmac.compare_digest(entry.code, code or ""):
            if consume:
                self._memory.pop(key, None)
            return True
        entry.attempts += 1
        return False


otp_store = OTPStore()


class TicketStore:
    """Single-use, short-lived tickets (e.g. SSO hand-off from the API to the SPA).

    A ticket is a 256-bit random string mapped to a small payload; redeeming it
    deletes it, so a leaked or replayed ticket is useless.
    """

    def __init__(self, ttl_seconds: int = 60) -> None:
        self.ttl = ttl_seconds
        self._memory: dict[str, tuple[float, str]] = {}

    async def issue(self, value: str) -> str:
        ticket = secrets.token_urlsafe(32)
        key = f"ticket:{ticket}"
        if not redis_breaker.is_open:
            try:
                await redis_client.set(key, value, ex=self.ttl)
                return ticket
            except Exception:
                redis_breaker.trip()
        self._memory[key] = (time.monotonic() + self.ttl, value)
        return ticket

    async def redeem(self, ticket: str) -> str | None:
        key = f"ticket:{ticket}"
        if not redis_breaker.is_open:
            try:
                value = await redis_client.getdel(key)
                if value is not None:
                    return value
            except Exception:
                redis_breaker.trip()
        entry = self._memory.pop(key, None)
        if entry is None or entry[0] < time.monotonic():
            return None
        return entry[1]


sso_tickets = TicketStore(ttl_seconds=60)

