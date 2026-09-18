from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, func, cast, Date
from datetime import datetime, timedelta
from app.models.code_submission import CodeSubmission
from app.api.deps import get_current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, log_audit_event, require_roles
from app.core.security import get_password_hash, verify_password
from app.models.institution import Institution
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserResponse, UserUpdate, UserPasswordUpdate

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
        department=user_in.department,
        section=user_in.section,
        batch_year=user_in.batch_year,
        roll_no=user_in.roll_no,
        phone=user_in.phone,
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
@router.post("/bulk-import", response_model=dict, status_code=status.HTTP_201_CREATED)
async def bulk_import_users(
    request: Request,
    payload: dict,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    from app.services.password_policy import generate_sequential_password
    users_data = payload.get("users", [])
    password_prefix = payload.get("password_prefix", "Exam@")
    
    count = 0
    for idx, user_dict in enumerate(users_data):
        email = user_dict.get("email", "").lower()
        if not email:
            continue
            
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            continue
            
        plain_pwd = generate_sequential_password(password_prefix, idx + 1)
        hashed_pwd = get_password_hash(plain_pwd)
        
        new_user = User(
            email=email,
            hashed_password=hashed_pwd,
            full_name=user_dict.get("full_name", "Unknown"),
            role=UserRole(user_dict.get("role", "candidate")),
            department=user_dict.get("department"),
            section=user_dict.get("section"),
            batch_year=user_dict.get("batch_year"),
            roll_no=user_dict.get("roll_no"),
            is_active=True,
            is_verified=True,
        )
        db.add(new_user)
        count += 1
        
    await db.commit()
    return {"status": "success", "imported_count": count}

@router.get("/me/activity")
async def get_my_activity(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Get submissions per day for the last 15 weeks
    cutoff_date = datetime.utcnow() - timedelta(days=105)
    
    query = (
        select(
            cast(CodeSubmission.created_at, Date).label("date"),
            func.count(CodeSubmission.id).label("count")
        )
        .where(CodeSubmission.candidate_id == current_user.id)
        .where(CodeSubmission.created_at >= cutoff_date)
        .group_by(cast(CodeSubmission.created_at, Date))
    )
    result = await db.execute(query)
    rows = result.all()
    
    # Calculate stats
    stats_query = select(func.count(func.distinct(CodeSubmission.session_id))).where(CodeSubmission.candidate_id == current_user.id)
    problems_solved = (await db.execute(stats_query)).scalar() or 0
    
    return {
        "problems_solved": problems_solved,
        "current_streak": 0,
        "max_streak": 0,
        "daily_counts": {str(row.date): row.count for row in rows}
    }

@router.put("/me", response_model=UserResponse)
async def update_user_me(
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if user_in.full_name is not None:
        current_user.full_name = user_in.full_name
    if user_in.phone is not None:
        current_user.phone = user_in.phone
    if user_in.email is not None:
        current_user.email = user_in.email

    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user

@router.put("/me/password", response_model=dict)
async def update_password_me(
    user_in: UserPasswordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(user_in.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    current_user.hashed_password = get_password_hash(user_in.new_password)
    db.add(current_user)
    await db.commit()
    return {"status": "success", "message": "Password updated successfully"}

@router.put("/{user_id}", response_model=UserResponse)
async def admin_update_user(
    user_id: uuid.UUID,
    user_in: dict,  # Using dict directly to bypass strict schema for now since we just defined it inline
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if "full_name" in user_in and user_in["full_name"]:
        user.full_name = user_in["full_name"]
    if "email" in user_in and user_in["email"]:
        user.email = user_in["email"]
    if "role" in user_in and user_in["role"]:
        try:
            user.role = UserRole(user_in["role"])
        except ValueError:
            pass
    if "password" in user_in and user_in["password"]:
        user.hashed_password = get_password_hash(user_in["password"])
        
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
