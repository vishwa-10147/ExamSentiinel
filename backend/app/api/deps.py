from collections import deque
from typing import AsyncGenerator, Callable, List, Optional
import uuid
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth_cookies import access_token_from_cookie, csrf_ok
from app.core.config import settings
from app.core.logging import logger
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole
from app.models.audit_log import AuditLog

# HTTP Bearer security scheme
bearer_scheme = HTTPBearer(auto_error=False)


def extract_client_ip(request: Optional[Request]) -> Optional[str]:
    """The client's IP address, as used for rate limits, sign-in throttling and audit logs.

    Headers sent by the client are never trusted on their own: anyone can send
    ``X-Forwarded-For`` or ``X-Real-IP`` with a different address on every request and so
    escape per-IP limits. Behind a load balancer, uvicorn's proxy-headers middleware resolves
    the client from ``X-Forwarded-For``, trusting only the proxies listed in
    ``FORWARDED_ALLOW_IPS`` (see docker-entrypoint.sh), and that result is ``request.client``.
    ``CLIENT_IP_HEADER`` names one header to use instead, for a proxy that sets it and strips
    any client-supplied copy (e.g. ``CF-Connecting-IP`` when only Cloudflare can reach the API).
    """
    if not request:
        return None
    if settings.CLIENT_IP_HEADER:
        value = (request.headers.get(settings.CLIENT_IP_HEADER) or "").split(",")[0].strip()
        if value:
            return value
    return request.client.host if request.client else None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency that authenticates JWT access token and returns current active User.

    The token comes from the ``Authorization: Bearer`` header (API clients) or the
    httpOnly session cookie (browsers; see app/core/auth_cookies.py).
    """
    if credentials and credentials.credentials:
        token = credentials.credentials
    else:
        token = access_token_from_cookie(request)
        if token and not csrf_ok(request):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing X-Requested-With header for a cookie-authenticated request",
            )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_type = payload.get("type")
    if token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type for authorization",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("user_id")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = uuid.UUID(str(user_id_str))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed user ID in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with token not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    # Single session enforcement: invalidate old browser sessions when a new login occurs
    token_sid = payload.get("sid")
    if token_sid and user.current_session_id and token_sid != user.current_session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Logged in from another browser/session. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_roles(allowed_roles: List[UserRole]) -> Callable:
    """Dependency factory enforcing role-based access control (RBAC) with audit logging."""
    async def role_checker(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if current_user.role not in allowed_roles:
            # Audit log unauthorized access attempts
            await log_audit_event(
                db=db,
                action="ACCESS_DENIED",
                resource_type="endpoint",
                resource_id=request.url.path,
                details={
                    "path": request.url.path,
                    "method": request.method,
                    "user_role": current_user.role.value,
                    "allowed_roles": [r.value for r in allowed_roles],
                },
                user_id=current_user.id,
                institution_id=current_user.institution_id,
                request=request,
            )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted for role: {current_user.role.value}",
            )
        return current_user

    return role_checker


async def log_audit_event(
    db: AsyncSession,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    user_id: Optional[uuid.UUID] = None,
    institution_id: Optional[uuid.UUID] = None,
    request: Optional[Request] = None,
) -> AuditLog:
    """Helper to record immutable audit log entries with safe user_agent truncation."""
    ip_address = extract_client_ip(request)
    raw_user_agent = request.headers.get("user-agent") if request else None
    user_agent = raw_user_agent[:500] if raw_user_agent else None

    audit_entry = AuditLog(
        institution_id=institution_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(audit_entry)
    await db.flush()
    return audit_entry


from app.core.redis_client import redis_breaker, redis_client
import time
from fastapi import Request

# Per-process sliding windows used when Redis is unavailable (see RateLimiter).
_local_windows: dict[str, "deque[float]"] = {}
_LOCAL_WINDOW_MAX_KEYS = 50_000


def _local_rate_limit(key: str, calls: int, period: int, now: float) -> None:
    window = _local_windows.get(key)
    if window is None:
        if len(_local_windows) >= _LOCAL_WINDOW_MAX_KEYS:
            _local_windows.clear()  # bounded memory; a reset only loosens limits briefly
        window = _local_windows[key] = deque()
    while window and window[0] <= now - period:
        window.popleft()
    if len(window) >= calls:
        logger.warning("rate_limit_exceeded", key=key, backend="local")
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too Many Requests")
    window.append(now)


def _user_key(request: Request) -> Optional[str]:
    """The user id from the request's access token (header or cookie), without a DB lookup."""
    header = request.headers.get("authorization", "")
    token = header[7:] if header.lower().startswith("bearer ") else access_token_from_cookie(request)
    if not token:
        return None
    try:
        payload = decode_token(token)
    except jwt.InvalidTokenError:
        return None
    return str(payload.get("user_id")) if payload.get("type") == "access" and payload.get("user_id") else None


def RateLimiter(calls: int, period: int, local_fallback: bool = False, per_user: bool = False):
    """
    Returns a FastAPI dependency that implements a sliding window rate limit using Redis.
    Uses MULTI/EXEC pipeline to ensure atomicity.

    Without Redis the limit is skipped, unless ``local_fallback`` is set: then a
    per-process window enforces it (used for code execution and authentication, which
    must stay limited even when Redis is down; with N workers the effective limit is
    N x calls). Failed sign-ins are throttled separately by ``FailedLoginThrottle``.

    ``per_user`` keys the window on the signed-in user instead of the client IP - needed for
    exam-day traffic, where a whole lab of students shares one NAT address.
    """
    async def rate_limit_dependency(request: Request):
        client_ip = extract_client_ip(request) or "127.0.0.1"
        identity = (_user_key(request) if per_user else None) or client_ip
        key = f"rate_limit:{request.url.path}:{identity}"
        now = time.time()
        if redis_breaker.is_open:
            if local_fallback:
                _local_rate_limit(key, calls, period, now)
            return  # Redis recently unreachable: rate limiting is best-effort
        
        try:
            # Redis MULTI/EXEC block for sliding window
            async with redis_client.pipeline(transaction=True) as pipe:
                # Remove scores older than (now - period)
                pipe.zremrangebyscore(key, 0, now - period)
                # Add current request timestamp
                pipe.zadd(key, {str(now): now})
                # Count requests in window
                pipe.zcard(key)
                # Set TTL to prevent stale keys
                pipe.expire(key, period)
                
                results = await pipe.execute()
            redis_breaker.succeeded()

            request_count = results[2]
            
            if request_count > calls:
                logger.warning("rate_limit_exceeded", ip=client_ip, path=request.url.path)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too Many Requests"
                )
        except Exception as e:
            if isinstance(e, HTTPException):
                raise e
            redis_breaker.trip()
            logger.debug(f"Redis rate limiter failed, bypassing: {e}")
            if local_fallback:
                _local_rate_limit(key, calls, period, now)
            
    return rate_limit_dependency


class FailedLoginThrottle:
    """Limits *failed* sign-in attempts - brute-force protection that never counts successful
    sign-ins. Two windows:

    - per (client IP, account): ``max_failures`` per ``period`` - stops one machine guessing;
    - per account, from any IP: ``account_max_failures`` per ``account_period`` - stops a
      guesser who rotates IP addresses (a botnet, or a misconfigured proxy trust). It is set
      high enough that a student mistyping cannot hit it, and its lock is short.

    Uses Redis when it is reachable and the in-process window otherwise (same windows as
    ``RateLimiter(local_fallback=True)``)."""

    def __init__(self, max_failures: int = 5, period: int = 60,
                 account_max_failures: int = 30, account_period: int = 900):
        self.max_failures, self.period = max_failures, period
        self.account_max_failures, self.account_period = account_max_failures, account_period

    def _keys(self, request: Request, email: str) -> tuple[str, str]:
        account = email.strip().lower()[:254]
        return f"login_failures:{extract_client_ip(request) or '127.0.0.1'}:{account}", f"login_failures_account:{account}"

    async def _count(self, key: str, now: float, add: bool, period: int) -> int:
        if not redis_breaker.is_open:
            try:
                async with redis_client.pipeline(transaction=True) as pipe:
                    pipe.zremrangebyscore(key, 0, now - period)
                    if add:
                        pipe.zadd(key, {str(now): now})
                    pipe.zcard(key)
                    pipe.expire(key, period)
                    results = await pipe.execute()
                redis_breaker.succeeded()
                return int(results[2] if add else results[1])
            except Exception:
                redis_breaker.trip()
        window = _local_windows.setdefault(key, deque())
        while window and window[0] <= now - period:
            window.popleft()
        if add:
            window.append(now)
        return len(window)

    async def check(self, request: Request, email: str) -> None:
        per_ip, per_account = self._keys(request, email)
        now = time.time()
        if await self._count(per_ip, now, add=False, period=self.period) >= self.max_failures:
            logger.warning("login_throttled", ip=extract_client_ip(request))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed sign-in attempts. Please wait a minute and try again.",
            )
        if await self._count(per_account, now, add=False, period=self.account_period) >= self.account_max_failures:
            logger.warning("login_throttled_account", ip=extract_client_ip(request))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed sign-in attempts for this account. Please wait 15 minutes or reset your password.",
            )

    async def record_failure(self, request: Request, email: str) -> None:
        per_ip, per_account = self._keys(request, email)
        now = time.time()
        await self._count(per_ip, now, add=True, period=self.period)
        await self._count(per_account, now, add=True, period=self.account_period)

    async def clear_account(self, email: str) -> None:
        """Lift the per-account lock, e.g. after the owner proved control with a reset code."""
        key = f"login_failures_account:{email.strip().lower()[:254]}"
        _local_windows.pop(key, None)
        if not redis_breaker.is_open:
            try:
                await redis_client.delete(key)
            except Exception:
                redis_breaker.trip()


failed_login_throttle = FailedLoginThrottle()
