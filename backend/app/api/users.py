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
    """Administrative user provisioning endpoint.

    Only accessible by users with the ADMIN role. Supports provisioning
    staff accounts (admin, proctor, reviewer, candidate).
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
