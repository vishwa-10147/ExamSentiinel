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
from app.models.audit_log import AuditLog
from sqlalchemy.orm import joinedload
import json
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
    from app.models.session import ExamSession
    from app.models.response import ExamResponse
    
    # Get activity per day for the last 15 weeks (105 days)
    cutoff_date = datetime.utcnow() - timedelta(days=105)
    daily_counts: Dict[str, int] = {}

    # 1. Query Code Submissions
    code_query = (
        select(
            cast(CodeSubmission.created_at, Date).label("date"),
            func.count(CodeSubmission.id).label("count")
        )
        .where(CodeSubmission.candidate_id == current_user.id)
        .where(CodeSubmission.created_at >= cutoff_date)
        .group_by(cast(CodeSubmission.created_at, Date))
    )
    code_res = await db.execute(code_query)
    for row in code_res.all():
        if row.date:
            daily_counts[str(row.date)] = daily_counts.get(str(row.date), 0) + row.count

    # 2. Query Exam Sessions started/submitted
    session_query = (
        select(
            cast(ExamSession.started_at, Date).label("date"),
            func.count(ExamSession.id).label("count")
        )
        .where(ExamSession.candidate_id == current_user.id)
        .where(ExamSession.started_at >= cutoff_date)
        .group_by(cast(ExamSession.started_at, Date))
    )
    session_res = await db.execute(session_query)
    for row in session_res.all():
        if row.date:
            daily_counts[str(row.date)] = daily_counts.get(str(row.date), 0) + row.count

    # 3. Calculate total problems solved / questions answered
    resp_query = select(func.count(ExamResponse.id)).join(ExamSession).where(ExamSession.candidate_id == current_user.id)
    resp_count = (await db.execute(resp_query)).scalar() or 0
    
    code_count_query = select(func.count(CodeSubmission.id)).where(CodeSubmission.candidate_id == current_user.id)
    code_count = (await db.execute(code_count_query)).scalar() or 0

    problems_solved = resp_count + code_count
    
    return {
        "problems_solved": problems_solved,
        "current_streak": 0,
        "max_streak": 0,
        "daily_counts": daily_counts
    }


@router.get("/me/stats")
async def get_my_candidate_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return live database account stats for the candidate (total exams taken and average score percentage)."""
    from app.models.session import ExamSession, SessionStatus
    from app.models.exam import ExamEnrollment
    
    query = select(ExamSession).where(ExamSession.candidate_id == current_user.id)
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    # Taken sessions include submitted, expired, or any session started by candidate
    taken_sessions = [
        s for s in sessions
        if s.status in (SessionStatus.SUBMITTED, SessionStatus.EXPIRED, "SUBMITTED", "EXPIRED")
        or s.submitted_at is not None
        or s.started_at is not None
    ]
    
    total_exams = len(taken_sessions)
    if total_exams == 0:
        enroll_query = select(ExamEnrollment).where(ExamEnrollment.candidate_id == current_user.id)
        enroll_res = await db.execute(enroll_query)
        total_exams = len(enroll_res.scalars().all())
        
    percentages = []
    for s in taken_sessions:
        if s.percentage is not None and s.percentage > 0:
            percentages.append(s.percentage)
        elif s.max_score and s.max_score > 0 and s.total_score is not None:
            percentages.append(round((s.total_score / s.max_score) * 100, 1))
            
    avg_score = round(sum(percentages) / len(percentages), 1) if percentages else 0.0
        
    return {
        "total_exams_taken": total_exams,
        "average_score_percentage": avg_score
    }


@router.get("/audit", response_model=List[dict])
async def list_audit_logs(
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
    db: AsyncSession = Depends(get_db),
):
    """Return recent audit events for the admin audit console."""
    limit = min(max(limit, 1), 500)
    offset = max(offset, 0)
    result = await db.execute(
        select(AuditLog)
        .options(joinedload(AuditLog.user))
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    logs = result.scalars().unique().all()
    return [
        {
            "id": str(log.id),
            "timestamp": log.created_at.isoformat(),
            "action": log.action,
            "user": log.user.full_name if log.user else "System",
            "role": log.user.role.value if log.user else "system",
            "ip_address": log.ip_address or "—",
            "status": "error" if log.action.endswith("_FAILED") else "success",
            "details": json.dumps(log.details) if log.details else None,
        }
        for log in logs
    ]

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
    if user_in.department is not None:
        current_user.department = user_in.department
    if user_in.section is not None:
        current_user.section = user_in.section
    if user_in.batch_year is not None:
        current_user.batch_year = user_in.batch_year

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
    user_in: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    old_role = user.role.value if user.role else "candidate"
    if "full_name" in user_in and user_in["full_name"]:
        user.full_name = user_in["full_name"]
    if "email" in user_in and user_in["email"]:
        user.email = user_in["email"].strip().lower()
    if "role" in user_in and user_in["role"]:
        try:
            user.role = UserRole(user_in["role"])
        except ValueError:
            pass
    if "is_active" in user_in:
        user.is_active = bool(user_in["is_active"])
    if "password" in user_in and user_in["password"]:
        user.hashed_password = get_password_hash(user_in["password"])
        
    db.add(user)

    if old_role != user.role.value:
        await log_audit_event(
            db=db,
            action="USER_ROLE_UPDATED",
            resource_type="user",
            resource_id=str(user.id),
            details={
                "email": user.email,
                "previous_role": old_role,
                "new_role": user.role.value,
                "updated_by": str(current_user.id),
            },
            user_id=current_user.id,
            institution_id=current_user.institution_id,
            request=request,
        )

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def admin_delete_user(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
):
    """Delete a user account permanently (Admin only)."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own admin account",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    try:
        from app.models.exam import Exam, ExamEnrollment
        from app.models.session import ExamSession
        from app.models.response import ExamResponse
        from app.models.code_submission import CodeSubmission
        from app.models.refresh_token import RefreshToken
        from app.models.proctoring_event import ProctoringEvent
        from app.models.review_case import ReviewCase, ReviewAction
        from app.models.audit_log import AuditLog
        from sqlalchemy import delete, update

        # Delete responses linked to user's exam sessions
        session_ids_res = await db.execute(select(ExamSession.id).where(ExamSession.candidate_id == user_id))
        session_ids = [row[0] for row in session_ids_res.all()]
        if session_ids:
            await db.execute(delete(ExamResponse).where(ExamResponse.session_id.in_(session_ids)))

        # Delete dependent records where user is candidate or owner
        await db.execute(delete(ExamEnrollment).where(ExamEnrollment.candidate_id == user_id))
        await db.execute(delete(ExamSession).where(ExamSession.candidate_id == user_id))
        await db.execute(delete(CodeSubmission).where(CodeSubmission.candidate_id == user_id))
        await db.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
        await db.execute(delete(ProctoringEvent).where(ProctoringEvent.candidate_id == user_id))
        await db.execute(delete(ReviewAction).where(ReviewAction.reviewer_id == user_id))
        await db.execute(delete(ReviewCase).where(ReviewCase.candidate_id == user_id))

        # Nullify foreign key references in parent models where user is creator/reviewer
        await db.execute(update(Exam).where(Exam.created_by == user_id).values({Exam.created_by: None}))
        await db.execute(update(AuditLog).where(AuditLog.user_id == user_id).values({AuditLog.user_id: None}))
        await db.execute(update(ProctoringEvent).where(ProctoringEvent.reviewed_by == user_id).values({ProctoringEvent.reviewed_by: None}))
        await db.execute(update(ReviewCase).where(ReviewCase.assigned_reviewer_id == user_id).values({ReviewCase.assigned_reviewer_id: None}))
        await db.execute(update(ReviewCase).where(ReviewCase.resolved_by == user_id).values({ReviewCase.resolved_by: None}))

        # Log audit trail
        await log_audit_event(
            db=db,
            action="USER_DELETED_BY_ADMIN",
            resource_type="user",
            resource_id=str(target_user.id),
            details={
                "email": target_user.email,
                "role": target_user.role.value if target_user.role else "unknown",
                "deleted_by": str(current_user.id),
            },
            user_id=current_user.id,
            institution_id=current_user.institution_id,
            request=request,
        )

        await db.delete(target_user)
        await db.commit()
        return {"status": "success", "message": f"User {target_user.email} and all associated data deleted successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to delete user: {str(e)}",
        )
