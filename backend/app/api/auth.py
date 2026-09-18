from datetime import datetime, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
import jwt
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db, log_audit_event, RateLimiter
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models.institution import Institution
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole
from app.schemas.auth import TokenRefreshRequest, TokenResponse
from app.schemas.user import UserCreate, UserLogin, UserResponse
import random
import redis.asyncio as redis
from pydantic import BaseModel


class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    email: str
    otp_code: str
    new_password: str

class OTPVerifyRequest(BaseModel):
    user_id: uuid.UUID
    otp_code: str

class LoginResponse(BaseModel):
    requires_2fa: bool
    user_id: uuid.UUID
    email: str
    message: str = "OTP sent to email"


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RateLimiter(calls=3, period=3600))])
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
    hashed_pwd = get_password_hash(user_in.password)
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


@router.post("/login")
async def login(
    credentials: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user credentials and issue signed JWT access and refresh tokens."""
    result = await db.execute(select(User).where(User.email == credentials.email.lower()))
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password):
        # Log failed login attempt for audit trail and brute-force visibility
        await log_audit_event(
            db=db,
            action="LOGIN_FAILED",
            resource_type="auth",
            resource_id=credentials.email.lower(),
            details={"email": credentials.email.lower(), "reason": "invalid_credentials"},
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

    token_data = {
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "institution_id": str(user.institution_id) if user.institution_id else None,
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
        details={"email": user.email, "role": user.role.value},
        user_id=user.id,
        institution_id=user.institution_id,
        request=request,
    )
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    refresh_req: TokenRefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Validate refresh token and issue a newly rotated token pair with single-use revocation."""
    try:
        payload = decode_token(refresh_req.refresh_token)
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

    token_data = {
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "institution_id": str(user.institution_id) if user.institution_id else None,
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

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke all active refresh tokens for the authenticated user and record audit log."""
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
    return {"message": "Successfully logged out and revoked active sessions"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Retrieve currently authenticated user profile and roles."""
    return current_user

@router.post("/forgot-password", dependencies=[Depends(RateLimiter(calls=3, period=600))])
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    user = result.scalar_one_or_none()
    if not user:
        # Silently succeed to prevent email enumeration
        return {"status": "success", "message": "If an account exists, an OTP has been sent."}
        
    otp_code = str(random.randint(100000, 999999))
    r = redis.from_url(str(settings.REDIS_URL))
    await r.setex(f"auth:forgot:{user.id}", 300, otp_code)
    await r.aclose()
    
    print(f"\n{'='*50}")
    print(f"MOCK EMAIL: To {user.email}")
    print(f"Subject: Password Reset Request")
    print(f"Your OTP is: {otp_code}. It expires in 5 minutes.")
    print(f"{'='*50}\n")
    
    return {"status": "success", "message": "If an account exists, an OTP has been sent."}

@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid OTP")
        
    r = redis.from_url(str(settings.REDIS_URL))
    cached_otp = await r.get(f"auth:forgot:{user.id}")
    await r.aclose()
    
    if not cached_otp or cached_otp.decode() != payload.otp_code:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OTP"
        )
        
    # Reset password
    user.hashed_password = get_password_hash(payload.new_password)
    db.add(user)
    await db.commit()
    
    # Delete OTP
    r = redis.from_url(str(settings.REDIS_URL))
    await r.delete(f"auth:forgot:{user.id}")
    await r.aclose()
    
    return {"status": "success", "message": "Password reset successfully."}
