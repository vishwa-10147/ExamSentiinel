# Milestone 1 Remediation Plan: Platform Foundation & Security Hardening

**Author:** `explorer_m1_remediation`  
**Working Directory:** `d:\vishwa47\v47Studio\ExamSentinel\.agents\explorer_m1_remediation\`  
**Target:** Milestone 1 Deliverables (`worker_m1`)  
**Date:** 2026-09-16  

---

## 1. Executive Summary & Defect Inventory

An exhaustive synthesis of independent challenger reports (`challenger_m1_1`, `challenger_m1_2`) and reviewer analysis (`reviewer_m1_2`) reveals that while Milestone 1 establishes a solid documentation suite, responsive Next.js frontend, and core FastAPI structure, **six critical-to-medium defects** prevent Milestone 1 gate approval:

| Defect ID | Severity | Area | Root Cause | Fix Strategy | Affected Files |
|---|---|---|---|---|---|
| **DEF-01** | **CRITICAL** | Authorization / RBAC | `POST /api/auth/register` applies client-supplied `role` directly, allowing anonymous public users to register as `admin`. | Unconditionally force `role = UserRole.CANDIDATE` on public registration. Create dedicated `POST /api/users` endpoint protected by `require_roles([UserRole.ADMIN])` for staff provisioning. | `backend/app/api/auth.py`<br>`backend/app/schemas/user.py`<br>`backend/app/api/users.py`<br>`backend/app/api/router.py` |
| **DEF-02** | **CRITICAL** | Session / Token Security | Refresh tokens lack persistent revocation tracking. Replaying an already-rotated refresh token succeeds repeatedly (RFC 6819 violation). | Introduce a database-backed `refresh_tokens` table tracking `jti`, `user_id`, `revoked`, and `expires_at`. Enforce single-use rotation and return HTTP 401 on replay attempt. | `backend/app/models/refresh_token.py`<br>`backend/app/models/__init__.py`<br>`backend/alembic/versions/001_initial_core_schema.py`<br>`backend/app/api/auth.py` |
| **DEF-03** | **CRITICAL** | Deployment / Infrastructure | `docker-compose.yml` configures `sandbox-worker` with `context: ./execution-workers`, but the directory does not exist in the repository, crashing `docker compose up -d` and `docker compose build`. | Scaffold the `execution-workers/` directory containing a production-grade `Dockerfile`, `requirements.txt`, and `runner.py` service. | `execution-workers/Dockerfile`<br>`execution-workers/requirements.txt`<br>`execution-workers/runner.py` |
| **DEF-04** | **HIGH** | Concurrency / Data Integrity | Concurrent duplicate registration requests trigger an unhandled database `IntegrityError` resulting in HTTP 500. Arbitrary `institution_id` also triggers foreign key crash. | Validate `institution_id` existence before user insertion. Wrap user creation and commit in `try...except IntegrityError` and return clean HTTP 400 Bad Request. | `backend/app/api/auth.py`<br>`backend/app/api/users.py` |
| **DEF-05** | **MEDIUM** | Audit Trail / Reliability | Failed logins and 403 Forbidden RBAC attempts leave zero records in `audit_logs`. Raw `User-Agent` headers > 512 bytes crash inserts with PostgreSQL `DataError`. | Add audit event logging for failed logins (`action="LOGIN_FAILED"`) and RBAC denials (`action="ACCESS_DENIED"`). Truncate incoming `user_agent` to 500 characters in `log_audit_event()`. | `backend/app/api/deps.py`<br>`backend/app/api/auth.py` |
| **DEF-06** | **MEDIUM** | Database Schema Parity | Alembic migration creates a native PostgreSQL enum `user_role_enum`, but SQLAlchemy `User.role` specifies `native_enum=False` (VARCHAR), causing `DatatypeMismatchError` under PostgreSQL `asyncpg`. | Harmonize `User.role` with `Enum(UserRole, name="user_role_enum", native_enum=True, length=32)` and align migration definition. | `backend/app/models/user.py`<br>`backend/alembic/versions/001_initial_core_schema.py` |

---

## 2. File-by-File Technical Remediation Specifications

### File 1: `backend/app/models/refresh_token.py` (NEW FILE)
- **Purpose:** Persistent tracking of issued refresh tokens with explicit JTI, user association, and revocation flag.
- **Specification:**
```python
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
import uuid
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import TimeStampedUUIDModel

if TYPE_CHECKING:
    from app.models.user import User


class RefreshToken(TimeStampedUUIDModel):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    jti: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="refresh_tokens")
```

---

### File 2: `backend/app/models/__init__.py`
- **Purpose:** Export `RefreshToken` model so `Base.metadata` automatically registers it for migrations and SQLite test schemas.
- **Changes:**
```python
from app.core.database import Base
from app.models.base import TimeStampedUUIDModel
from app.models.institution import Institution
from app.models.user import User, UserRole
from app.models.audit_log import AuditLog
from app.models.refresh_token import RefreshToken

__all__ = [
    "Base",
    "TimeStampedUUIDModel",
    "Institution",
    "User",
    "UserRole",
    "AuditLog",
    "RefreshToken",
]
```

---

### File 3: `backend/app/models/user.py`
- **Purpose:** Harmonize PostgreSQL native enum definition with Alembic migration.
- **Lines to Edit:** Lines 26–36:
```python
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role_enum",
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=True,
            length=32,
        ),
        default=UserRole.CANDIDATE,
        nullable=False,
        index=True,
    )
```

---

### File 4: `backend/alembic/versions/001_initial_core_schema.py`
- **Purpose:** Add `refresh_tokens` table creation and ensure enum types are cleanly created and dropped.
- **Changes in `upgrade()`:**
```python
    # 2. Create users table (ensure native_enum is explicit)
    user_role_enum = sa.Enum("admin", "proctor", "reviewer", "candidate", name="user_role_enum")
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            user_role_enum,
            nullable=False,
            server_default="candidate",
        ),
        sa.Column("institution_id", sa.Uuid(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    ...
    # 3. Create refresh_tokens table
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_refresh_tokens_id"), "refresh_tokens", ["id"], unique=False)
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"], unique=False)
    op.create_index(op.f("ix_refresh_tokens_jti"), "refresh_tokens", ["jti"], unique=True)
    op.create_index(op.f("ix_refresh_tokens_revoked"), "refresh_tokens", ["revoked"], unique=False)
```
- **Changes in `downgrade()`:**
```python
    op.drop_table("refresh_tokens")
    op.drop_table("audit_logs")
    op.drop_table("users")
    op.drop_table("institutions")
    op.execute("DROP TYPE IF EXISTS user_role_enum")
```

---

### File 5: `backend/app/schemas/user.py`
- **Purpose:** Ensure `UserCreate` schema supports role specification without validation errors while documenting role assignment boundaries.
- **Specification:**
```python
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)
    role: UserRole = UserRole.CANDIDATE
    institution_id: Optional[uuid.UUID] = None
```
*(Note: Public registration ignores client-supplied `role` and forces `UserRole.CANDIDATE`. Admin provisioning route uses `role` directly).*

---

### File 6: `backend/app/api/deps.py`
- **Purpose:**
  1. Truncate `user_agent` to <= 500 characters to prevent database overflow crashes.
  2. Emit `AuditLog` entry with `action="ACCESS_DENIED"` whenever `require_roles` denies access.
- **Changes in `deps.py`:**
```python
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
```

---

### File 7: `backend/app/api/auth.py`
- **Purpose:**
  1. Force `role = UserRole.CANDIDATE` unconditionally on public registration.
  2. Validate `institution_id` existence to prevent foreign key errors.
  3. Wrap registration in `try...except IntegrityError` to prevent unhandled 500 race condition crashes.
  4. Log audit event on failed login (`LOGIN_FAILED`).
  5. Store issued refresh token JTI in `refresh_tokens` on `login` and `refresh`.
  6. Enforce single-use refresh token rotation: invalidate old JTI, reject already-revoked JTIs with HTTP 401.
  7. Add `POST /api/auth/logout` endpoint.
- **Key Implementation Sections:**

#### 1. Registration (`POST /api/auth/register`)
```python
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
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

    await db.refresh(user)
    return user
```

#### 2. Login (`POST /api/auth/login`)
```python
@router.post("/login", response_model=TokenResponse)
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
```

#### 3. Refresh Token Rotation (`POST /api/auth/refresh`)
```python
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
```

#### 4. Logout (`POST /api/auth/logout`)
```python
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
```

---

### File 8: `backend/app/api/users.py` (NEW FILE)
- **Purpose:** Dedicated administrator endpoint for provisioning privileged accounts (`admin`, `proctor`, `reviewer`, `candidate`) protected by `require_roles([UserRole.ADMIN])`.
- **Specification:**
```python
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, log_audit_event, require_roles
from app.core.security import get_password_hash
from app.models.institution import Institution
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_user_by_admin(
    user_in: UserCreate,
    request: Request,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """
    Administrative user provisioning endpoint.
    Only accessible by users with the ADMIN role.
    Supports provisioning staff accounts (admin, proctor, reviewer, candidate).
    """
    # Verify institution existence if provided
    if user_in.institution_id:
        inst_res = await db.execute(
            select(Institution).where(Institution.id == user_in.institution_id)
        )
        if not inst_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid institution_id: institution does not exist",
            )

    # Check for existing user by email
    existing_result = await db.execute(select(User).where(User.email == user_in.email.lower()))
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists",
        )

    # Create user with admin-specified role
    hashed_pwd = get_password_hash(user_in.password)
    new_user = User(
        email=user_in.email.lower(),
        hashed_password=hashed_pwd,
        full_name=user_in.full_name,
        role=user_in.role,  # Administrator is authorized to assign any role
        institution_id=user_in.institution_id,
        is_active=True,
        is_verified=True,
    )

    try:
        db.add(new_user)
        await db.flush()

        # Log audit trail
        await log_audit_event(
            db=db,
            action="USER_PROVISIONED_BY_ADMIN",
            resource_type="user",
            resource_id=str(new_user.id),
            details={
                "email": new_user.email,
                "role": new_user.role.value,
                "provisioned_by": str(current_user.id),
            },
            user_id=current_user.id,
            institution_id=current_user.institution_id,
            request=request,
        )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists",
        )

    await db.refresh(new_user)
    return new_user


@router.get("", response_model=List[UserResponse])
@router.get("/", response_model=List[UserResponse], include_in_schema=False)
async def list_users(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """List registered users (Admin only)."""
    result = await db.execute(select(User).offset(skip).limit(limit))
    return result.scalars().all()
```

---

### File 9: `backend/app/api/router.py`
- **Purpose:** Mount the new `users` router onto the main `api_router`.
- **Changes:**
```python
from fastapi import APIRouter, Depends
from app.api import auth, health, users
from app.api.deps import get_current_user, require_roles
from app.models.user import User, UserRole

api_router = APIRouter(prefix="/api")

# Mount auth routes (/api/auth/register, /login, /refresh, /me, /logout)
api_router.include_router(auth.router)

# Mount user management routes (/api/users)
api_router.include_router(users.router)

# Mount health routes (/api/health)
api_router.include_router(health.router)

# RBAC verification endpoints for integration tests and role validation
rbac_test_router = APIRouter(prefix="/rbac-test", tags=["RBAC Test"])
...
api_router.include_router(rbac_test_router)
```

---

### File 10: `execution-workers/Dockerfile` (NEW FILE)
- **Purpose:** Provide build context for the `sandbox-worker` service in `docker-compose.yml`.
- **Specification:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY runner.py .

CMD ["python", "runner.py"]
```

---

### File 11: `execution-workers/requirements.txt` (NEW FILE)
- **Purpose:** Worker dependencies.
- **Specification:**
```
redis>=5.0.0
pydantic>=2.5.0
structlog>=24.1.0
```

---

### File 12: `execution-workers/runner.py` (NEW FILE)
- **Purpose:** Standalone runner service responding to lifecycle signals and connecting to Redis.
- **Specification:**
```python
"""ExamSentinel Execution Worker Runner.

Scaffolded worker daemon connecting to Redis queue for isolated code execution.
"""

import os
import signal
import sys
import time
import structlog

logger = structlog.get_logger()

# Configuration from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
SANDBOX_QUEUE = os.getenv("SANDBOX_REDIS_QUEUE", "examsentinel:sandbox:queue")
CPU_LIMIT = float(os.getenv("SANDBOX_CPU_LIMIT", "1.0"))
MEMORY_LIMIT_MB = int(os.getenv("SANDBOX_MEMORY_LIMIT_MB", "256"))
TIMEOUT_SEC = float(os.getenv("SANDBOX_TIMEOUT_SEC", "5.0"))

RUNNING = True


def handle_shutdown(signum, frame):
    global RUNNING
    logger.info("Shutdown signal received", signal=signum)
    RUNNING = False


def main():
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    logger.info(
        "ExamSentinel execution worker started",
        redis_url=REDIS_URL,
        queue=SANDBOX_QUEUE,
        cpu_limit=CPU_LIMIT,
        memory_limit_mb=MEMORY_LIMIT_MB,
        timeout_sec=TIMEOUT_SEC,
    )

    while RUNNING:
        try:
            # Heartbeat loop awaiting Milestone 4 execution queue jobs
            time.sleep(5)
        except KeyboardInterrupt:
            break

    logger.info("ExamSentinel execution worker stopped cleanly")
    sys.exit(0)


if __name__ == "__main__":
    main()
```

---

### File 13: `backend/tests/test_remediation_m1.py` (NEW TEST SUITE)
- **Purpose:** Explicit regression and validation test suite covering all six remediated defects to ensure no regression in subsequent milestones.
- **Specification:**
```python
import asyncio
from datetime import datetime, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.institution import Institution
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole
from tests.conftest import test_async_session_maker


@pytest.mark.asyncio
async def test_public_registration_forces_candidate_role(async_client: AsyncClient, test_institution: Institution):
    """DEF-01: Verify public registration unconditionally forces CANDIDATE role even when admin is requested."""
    payload = {
        "email": "test_candidate_forced@sentinel.edu",
        "password": "Password123!",
        "full_name": "Forced Candidate",
        "role": "admin",
        "institution_id": str(test_institution.id),
    }
    res = await async_client.post("/api/auth/register", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["role"] == "candidate"


@pytest.mark.asyncio
async def test_admin_user_provisioning_endpoint(async_client: AsyncClient, seed_users, test_institution: Institution):
    """DEF-01: Verify authenticated admin can provision proctor and reviewer accounts via POST /api/users."""
    login_res = await async_client.post("/api/auth/login", json={"email": "admin@sentinel.edu", "password": "AdminPass123!"})
    admin_token = login_res.json()["access_token"]

    # Provision a proctor
    proctor_payload = {
        "email": "new_proctor@sentinel.edu",
        "password": "ProctorPassword123!",
        "full_name": "New Staff Proctor",
        "role": "proctor",
        "institution_id": str(test_institution.id),
    }
    res = await async_client.post(
        "/api/users",
        json=proctor_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["role"] == "proctor"
    assert data["email"] == "new_proctor@sentinel.edu"


@pytest.mark.asyncio
async def test_admin_user_provisioning_forbidden_for_candidate(async_client: AsyncClient, seed_users):
    """DEF-01: Verify candidate cannot access POST /api/users."""
    login_res = await async_client.post("/api/auth/login", json={"email": "candidate@sentinel.edu", "password": "CandidatePass123!"})
    cand_token = login_res.json()["access_token"]

    res = await async_client.post(
        "/api/users",
        json={"email": "illegal@sentinel.edu", "password": "Password123!", "full_name": "Illegal", "role": "admin"},
        headers={"Authorization": f"Bearer {cand_token}"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_refresh_token_revocation_and_replay_block(async_client: AsyncClient, seed_users):
    """DEF-02: Verify refresh token single-use rotation and replay rejection (HTTP 401)."""
    login_res = await async_client.post("/api/auth/login", json={"email": "proctor@sentinel.edu", "password": "ProctorPass123!"})
    r1 = login_res.json()["refresh_token"]

    # First rotation: legitimate
    res1 = await async_client.post("/api/auth/refresh", json={"refresh_token": r1})
    assert res1.status_code == 200
    r2 = res1.json()["refresh_token"]
    assert r2 != r1

    # Second rotation with r1: MUST return 401 Unauthorized
    res2 = await async_client.post("/api/auth/refresh", json={"refresh_token": r1})
    assert res2.status_code == 401
    assert "revoked" in res2.json()["detail"].lower() or "already used" in res2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_concurrency_duplicate_registration(async_client: AsyncClient, test_institution: Institution):
    """DEF-04: Verify concurrent duplicate registrations return 400 Bad Request without 500 crashes."""
    payload = {
        "email": "concurrent_test@sentinel.edu",
        "password": "Password123!",
        "full_name": "Concurrent Tester",
        "role": "candidate",
        "institution_id": str(test_institution.id),
    }
    tasks = [async_client.post("/api/auth/register", json=payload) for _ in range(5)]
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    status_codes = [r.status_code for r in responses if hasattr(r, "status_code")]

    assert 201 in status_codes
    assert status_codes.count(201) == 1
    assert 500 not in status_codes
    for sc in status_codes:
        assert sc in [201, 400]


@pytest.mark.asyncio
async def test_invalid_institution_id_registration(async_client: AsyncClient):
    """DEF-04: Verify non-existent institution_id returns 400 Bad Request instead of 500."""
    import uuid
    payload = {
        "email": "invalid_inst@sentinel.edu",
        "password": "Password123!",
        "full_name": "Invalid Inst",
        "role": "candidate",
        "institution_id": str(uuid.uuid4()),
    }
    res = await async_client.post("/api/auth/register", json=payload)
    assert res.status_code == 400
    assert "institution" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_failed_login_audit_trail(async_client: AsyncClient, seed_users):
    """DEF-05: Verify failed login writes audit log with action LOGIN_FAILED."""
    res = await async_client.post("/api/auth/login", json={"email": "admin@sentinel.edu", "password": "BadPassword!"})
    assert res.status_code == 401

    async with test_async_session_maker() as session:
        logs = (await session.execute(
            select(AuditLog).where(AuditLog.action == "LOGIN_FAILED")
        )).scalars().all()
        assert len(logs) > 0
        assert logs[-1].resource_id == "admin@sentinel.edu"


@pytest.mark.asyncio
async def test_access_denied_audit_trail(async_client: AsyncClient, seed_users):
    """DEF-05: Verify 403 access denial writes audit log with action ACCESS_DENIED."""
    login_res = await async_client.post("/api/auth/login", json={"email": "candidate@sentinel.edu", "password": "CandidatePass123!"})
    token = login_res.json()["access_token"]

    res = await async_client.get("/api/rbac-test/admin-only", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403

    async with test_async_session_maker() as session:
        logs = (await session.execute(
            select(AuditLog).where(AuditLog.action == "ACCESS_DENIED")
        )).scalars().all()
        assert len(logs) > 0
        assert logs[-1].resource_id == "/api/rbac-test/admin-only"


@pytest.mark.asyncio
async def test_user_agent_safe_truncation(async_client: AsyncClient, seed_users):
    """DEF-05: Verify giant user-agent (>512 chars) does not crash login."""
    huge_agent = "AgentBot/" + ("Z" * 1200)
    res = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@sentinel.edu", "password": "AdminPass123!"},
        headers={"User-Agent": huge_agent},
    )
    assert res.status_code == 200
```

---

## 3. Worker Implementation Sequence

The remediation should be implemented in this exact sequential order to maintain zero broken intermediary states:

1. **Step 1: Scaffolding `execution-workers/` Directory**
   - Create directory `execution-workers/`
   - Write `execution-workers/Dockerfile`
   - Write `execution-workers/requirements.txt`
   - Write `execution-workers/runner.py`
   - *Validates:* `test_docker_compose_build_contexts_exist` in `test_adversarial_m1_2.py`.

2. **Step 2: Database Models & Migration Parity**
   - Create `backend/app/models/refresh_token.py`
   - Update `backend/app/models/__init__.py` to export `RefreshToken`
   - Update `backend/app/models/user.py` to set `name="user_role_enum", native_enum=True`
   - Update `backend/alembic/versions/001_initial_core_schema.py` to include `refresh_tokens` table and explicit native enum
   - *Validates:* Schema consistency and model auto-registration.

3. **Step 3: Dependency Security & Audit Logging Hardening**
   - In `backend/app/api/deps.py`:
     - Truncate `user_agent` to `raw_user_agent[:500]` in `log_audit_event()`
     - Add `ACCESS_DENIED` audit logging in `require_roles()`
   - *Validates:* `test_audit_log_user_agent_buffer_overflow` and `test_audit_log_completeness_unauthorized_rbac_probe`.

4. **Step 4: Authentication & Registration Hardening**
   - In `backend/app/api/auth.py`:
     - Hardcode `role = UserRole.CANDIDATE` in `register_user`
     - Validate `institution_id` existence
     - Wrap database commit in `try...except IntegrityError` (return 400)
     - Record `LOGIN_FAILED` audit logs on invalid credentials / inactive account
     - Track `jti` in `refresh_tokens` on `login` and `refresh`
     - Implement single-use rotation and replay detection in `refresh_access_token` (HTTP 401)
     - Add `POST /api/auth/logout`
   - *Validates:* `test_public_registration_admin_role_escalation`, `test_refresh_token_replay_vulnerability`, `test_concurrent_duplicate_registration_race_condition`, and `test_audit_log_completeness_failed_login_attempt`.

5. **Step 5: Administrator User Provisioning Endpoint**
   - Create `backend/app/api/users.py` with `POST /api/users` and `GET /api/users`
   - Mount router in `backend/app/api/router.py`
   - *Validates:* Proper RBAC-secured provisioning for staff accounts (`admin`, `proctor`, `reviewer`).

6. **Step 6: Remediation Test Suite**
   - Create `backend/tests/test_remediation_m1.py`
   - Run full test suite across all files.

---

## 4. Verification Protocol

Independent verification can be executed as follows:

1. **Verify Execution Worker Scaffold:**
   ```bash
   python -c "import yaml, os; compose = yaml.safe_load(open('docker-compose.yml')); assert os.path.exists('execution-workers/Dockerfile')"
   ```
   *Expected:* Exits cleanly with code 0.

2. **Verify Python Test Suites:**
   ```bash
   cd backend
   pytest tests/test_adversarial.py -v
   pytest tests/test_adversarial_m1_2.py -v
   pytest tests/test_auth.py -v
   pytest tests/test_rbac.py -v
   pytest tests/test_remediation_m1.py -v
   ```
   *Expected:* All tests pass with 0 failures, 0 errors.

3. **Verify Privilege Escalation Fix:**
   - Attempt: `POST /api/auth/register` with `{"role": "admin"}`.
   - Result: Response JSON must contain `"role": "candidate"`.

4. **Verify Refresh Token Replay Fix:**
   - Attempt: Replay a used refresh token to `POST /api/auth/refresh`.
   - Result: Response status must be HTTP 401 with detail indicating token revoked or already used.

5. **Verify Concurrency Handling:**
   - Attempt: Simultaneous duplicate registrations with identical email.
   - Result: Exactly one returns 201; all others return clean HTTP 400 Bad Request with zero 500 crashes.
