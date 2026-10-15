from datetime import datetime, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
import jwt
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import failed_login_throttle, get_current_user, get_db, log_audit_event, RateLimiter
from app.core.auth_cookies import clear_auth_cookies, refresh_token_from_cookie, set_auth_cookies, wants_cookie_session
from app.core.config import settings
from app.core.logging import logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash_async,
    verify_password_async,
)
from app.models.institution import Institution
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole
from app.schemas.auth import TokenRefreshRequest, TokenResponse
from app.schemas.user import UserCreate, UserLogin, UserResponse
from pydantic import BaseModel
from app.services.email_service import email_service
from app.services.otp_store import otp_store
from app.services.email_templates import get_base_template


class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    email: str
    otp_code: str
    new_password: str

class VerifyForgotOTPRequest(BaseModel):
    email: str
    otp_code: str

class OTPVerifyRequest(BaseModel):
    user_id: uuid.UUID
    otp_code: str

class LoginResponse(BaseModel):
    requires_2fa: bool
    user_id: uuid.UUID
    email: str
    message: str = "OTP sent to email"


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RateLimiter(calls=3, period=3600, local_fallback=True))])
async def register_user(
    user_in: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user account as CANDIDATE with secure password hashing and audit logging."""
    # Pre-validate institution_id if provided
    if user_in.institution_id:
        inst_res = await db.execute(
            select(Institution).where(Institution.id == user_in.institution_id)
        )
        if not inst_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid institution_id: institution does not exist",
            )

    # Check if user already exists
    existing_result = await db.execute(select(User).where(User.email == user_in.email.lower()))
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists",
        )

    # Hash password and create user - PUBLIC REGISTRATION FORCES CANDIDATE ROLE
    hashed_pwd = await get_password_hash_async(user_in.password)
    user = User(
        email=user_in.email.lower(),
        hashed_password=hashed_pwd,
        full_name=user_in.full_name,
        role=UserRole.CANDIDATE,  # Enforce candidate role unconditionally
        institution_id=user_in.institution_id,
        is_active=True,
        is_verified=True,
    )

    try:
        db.add(user)
        await db.flush()

        # Log registration in audit trail
        await log_audit_event(
            db=db,
            action="USER_REGISTER",
            resource_type="user",
            resource_id=str(user.id),
            details={"email": user.email, "role": user.role.value},
            user_id=user.id,
            institution_id=user.institution_id,
            request=request,
        )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists",
        )

    return user


def session_response(request: Request, tokens: TokenResponse):
    """Return tokens in the body (API clients) or as httpOnly cookies (browsers in cookie mode)."""
    if not wants_cookie_session(request):
        return tokens
    body = tokens.model_dump(mode="json")
    body["access_token"] = body["refresh_token"] = None
    response = JSONResponse(body)
    set_auth_cookies(response, tokens.access_token, tokens.refresh_token)
    return response


async def issue_login_session(db: AsyncSession, user: User, request: Request, method: str):
    """Start a new browser session for *user* (password or SSO login).

    Enforces one active browser per user, rotates refresh tokens and audits
    the login with the method used.
    """
    # Generate a fresh session ID for single-browser login enforcement
    session_id = str(uuid.uuid4())
    user.current_session_id = session_id
    db.add(user)

    # Revoke all previous refresh tokens for this user so old browser sessions cannot refresh
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked.is_(False))
        .values(revoked=True)
    )

    token_data = {
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "institution_id": str(user.institution_id) if user.institution_id else None,
        "sid": session_id,
    }

    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    # Persist refresh token in database for single-use rotation and revocation tracking
    refresh_payload = decode_token(refresh_token)
    refresh_entry = RefreshToken(
        user_id=user.id,
        jti=refresh_payload["jti"],
        revoked=False,
        expires_at=datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc),
    )
    db.add(refresh_entry)

    # Log audit event
    await log_audit_event(
        db=db,
        action="USER_LOGIN",
        resource_type="auth",
        resource_id=str(user.id),
        details={"email": user.email, "role": user.role.value, "sid": session_id, "method": method},
        user_id=user.id,
        institution_id=user.institution_id,
        request=request,
    )
    await db.commit()

    return session_response(request, TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    ))


@router.post("/login", dependencies=[Depends(RateLimiter(calls=settings.LOGIN_RATE_LIMIT_PER_IP, period=60, local_fallback=True))])
async def login(
    credentials: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user credentials and issue signed JWT access and refresh tokens."""
    clean_email = credentials.email.strip().lower()
    # Brute-force protection: 5 failed attempts per minute per (IP, account); the per-IP limit
    # above (LOGIN_RATE_LIMIT_PER_IP) covers spraying many accounts.
    await failed_login_throttle.check(request, clean_email)
    result = await db.execute(select(User).where(User.email == clean_email))
    user = result.scalar_one_or_none()

    if not user or not await verify_password_async(credentials.password, user.hashed_password):
        await failed_login_throttle.record_failure(request, clean_email)
        # Log failed login attempt for audit trail and brute-force visibility
        await log_audit_event(
            db=db,
            action="LOGIN_FAILED",
            resource_type="auth",
            resource_id=clean_email,
            details={"email": clean_email, "reason": "invalid_credentials"},
            user_id=user.id if user else None,
            institution_id=user.institution_id if user else None,
            request=request,
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        await log_audit_event(
            db=db,
            action="LOGIN_FAILED",
            resource_type="auth",
            resource_id=str(user.id),
            details={"email": user.email, "reason": "inactive_account"},
            user_id=user.id,
            institution_id=user.institution_id,
            request=request,
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive. Please contact your administrator.",
        )

    return await issue_login_session(db, user, request, method="password")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    request: Request,
    refresh_req: TokenRefreshRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Validate refresh token and issue a newly rotated token pair with single-use revocation.

    Browsers send no body: the refresh token comes from the httpOnly cookie.
    """
    raw_refresh = (refresh_req.refresh_token if refresh_req else None) or refresh_token_from_cookie(request)
    if not raw_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token was not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_token(raw_refresh)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type: expected refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("user_id")
    try:
        user_id = uuid.UUID(str(user_id_str))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed user ID in refresh token",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User for given refresh token not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    # Validate single session ID
    token_sid = payload.get("sid")
    if token_sid and user.current_session_id and token_sid != user.current_session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Logged in from another browser/session. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check refresh token JTI in persistent storage
    jti = payload.get("jti")
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token: missing JTI identifier",
        )

    token_result = await db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
    token_record = token_result.scalar_one_or_none()

    # Replay detection: If token was not found or has already been revoked
    if token_record is None or token_record.revoked:
        # Suspected token compromise: revoke all active tokens for this user
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user.id)
            .values(revoked=True)
        )
        await log_audit_event(
            db=db,
            action="TOKEN_REPLAY_DETECTED",
            resource_type="auth",
            resource_id=str(user.id),
            details={"email": user.email, "jti": jti, "warning": "Replay of revoked refresh token detected"},
            user_id=user.id,
            institution_id=user.institution_id,
            request=request,
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked or already used",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Invalidate current refresh token (single-use rotation)
    token_record.revoked = True

    effective_sid = user.current_session_id or token_sid
    token_data = {
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "institution_id": str(user.institution_id) if user.institution_id else None,
        "sid": effective_sid,
    }

    new_access_token = create_access_token(data=token_data)
    new_refresh_token = create_refresh_token(data=token_data)

    new_payload = decode_token(new_refresh_token)
    new_refresh_entry = RefreshToken(
        user_id=user.id,
        jti=new_payload["jti"],
        revoked=False,
        expires_at=datetime.fromtimestamp(new_payload["exp"], tz=timezone.utc),
    )
    db.add(new_refresh_entry)

    await log_audit_event(
        db=db,
        action="TOKEN_REFRESH",
        resource_type="auth",
        resource_id=str(user.id),
        details={"email": user.email},
        user_id=user.id,
        institution_id=user.institution_id,
        request=request,
    )
    await db.commit()

    return session_response(request, TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    ))


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke all active refresh tokens for the authenticated user and record audit log."""
    current_user.current_session_id = None
    db.add(current_user)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == current_user.id)
        .values(revoked=True)
    )
    await log_audit_event(
        db=db,
        action="USER_LOGOUT",
        resource_type="auth",
        resource_id=str(current_user.id),
        details={"email": current_user.email},
        user_id=current_user.id,
        institution_id=current_user.institution_id,
        request=request,
    )
    await db.commit()
    response = JSONResponse({"message": "Successfully logged out and revoked active sessions"})
    clear_auth_cookies(response)
    return response


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Retrieve currently authenticated user profile and roles."""
    return current_user

_RESET_GENERIC = "If an account exists for that email, a verification code has been sent."


@router.post("/forgot-password", dependencies=[Depends(RateLimiter(calls=15, period=300, local_fallback=True))])
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send a reset code. The response is identical whether or not the email
    is registered, so the endpoint can't be used to discover accounts."""
    email = payload.email.strip().lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if not user or not user.is_active:
        return {"status": "success", "message": _RESET_GENERIC}

    otp_code = await otp_store.issue("password-reset", str(user.id))
    html_body = get_base_template(
        f"<h3>Password reset request</h3><p>Your one-time password is <strong>{otp_code}</strong>.</p>"
        "<p>This code expires in 5 minutes. If you did not request this, you can ignore this email.</p>"
    )
    text_body = f"Your ExamSentinel password reset OTP is {otp_code}. It expires in 5 minutes."
    delivered, error_reason = await email_service.send_with_reason([user.email], "ExamSentinel password reset OTP", html_body, text_body)
    if not delivered:
        logger.warning("password_reset_email_failed", user_id=str(user.id), reason=error_reason)
        if settings.DEBUG:
            # Local development without an email provider: surface the code in the server log.
            logger.info("password_reset_otp_dev_only", email=user.email, otp=otp_code)
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="We couldn't send the verification email right now. Please try again shortly.",
            )
    return {"status": "success", "message": _RESET_GENERIC}


@router.post("/verify-forgot-otp", dependencies=[Depends(RateLimiter(calls=20, period=300, local_fallback=True))])
async def verify_forgot_otp(
    payload: VerifyForgotOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    user = (await db.execute(select(User).where(User.email == payload.email.strip().lower()))).scalar_one_or_none()
    if not user or not await otp_store.verify("password-reset", str(user.id), payload.otp_code, consume=False):
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired 6-digit code. Request a new code if you've tried several times.",
        )
    return {"status": "success", "message": "OTP code verified successfully."}


@router.post("/reset-password", dependencies=[Depends(RateLimiter(calls=20, period=300, local_fallback=True))])
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    if len(payload.new_password) < 8 or len(payload.new_password) > 128:
        raise HTTPException(status_code=422, detail="Password must be 8-128 characters long.")
    user = (await db.execute(select(User).where(User.email == payload.email.strip().lower()))).scalar_one_or_none()
    if not user or not await otp_store.verify("password-reset", str(user.id), payload.otp_code, consume=True):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    user.hashed_password = await get_password_hash_async(payload.new_password)
    # Sign out everywhere: a reset usually means the old password is compromised.
    user.current_session_id = None
    await db.execute(
        update(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked.is_(False)).values(revoked=True)
    )
    await log_audit_event(db=db, action="PASSWORD_RESET", resource_type="user", resource_id=str(user.id),
                          details={}, user_id=user.id, institution_id=user.institution_id)
    await db.commit()
    await failed_login_throttle.clear_account(user.email)
    return {"status": "success", "message": "Password reset successfully."}
