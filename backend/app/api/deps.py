from typing import AsyncGenerator, Callable, List, Optional
import uuid
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole
from app.models.audit_log import AuditLog

# HTTP Bearer security scheme
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency that authenticates JWT access token and returns current active User."""
    if not credentials or not credentials.credentials:
        print("MISSING CREDENTIALS! Headers:", request.headers)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
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
    ip_address = request.client.host if request and request.client else None
    raw_user_agent = request.headers.get("user-agent") if request else None
    # Truncate user_agent to 500 characters to avoid VARCHAR(512) database overflow errors
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


from app.core.redis_client import redis_client
import time
from fastapi import Request

def RateLimiter(calls: int, period: int):
    """
    Sliding window rate limiter using Redis.
    calls: max number of requests allowed.
    period: time window in seconds.
    """
    async def rate_limit_dependency(request: Request):
        client_ip = request.client.host if request.client else "127.0.0.1"
        # Fallback to forwarded headers if behind proxy
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0]
            
        key = f"rate_limit:{request.url.path}:{client_ip}"
        now = time.time()
        
        # Redis MULTI/EXEC block for sliding window
        async with redis_client.pipeline(transaction=True) as pipe:
            # Remove scores older than (now - period)
            pipe.zremrangebyscore(key, 0, now - period)
            # Add current request timestamp
            pipe.zadd(key, {str(now): now})
            # Count requests in window
            pipe.zcard(key)
            # Set expiry to prevent lingering keys
            pipe.expire(key, period)
            
            results = await pipe.execute()
            
        request_count = results[2]
        
        if request_count > calls:
            raise HTTPException(
                status_code=429,
                detail="Too Many Requests. Please try again later."
            )
            
    return rate_limit_dependency
