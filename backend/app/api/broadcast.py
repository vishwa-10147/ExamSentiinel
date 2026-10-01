from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
import uuid

from app.api.deps import get_db, require_roles, log_audit_event
from app.models.user import User, UserRole
from app.models.exam import Exam, ExamEnrollment
from app.models.session import ExamSession
from app.services.email_service import email_service
from app.services.email_templates import get_custom_broadcast_template

router = APIRouter(prefix="/admin/broadcast", tags=["Broadcast"])

class BroadcastRequest(BaseModel):
    target_role: Optional[UserRole] = None
    all_users: bool = False
    exam_id: Optional[uuid.UUID] = None
    user_ids: Optional[List[uuid.UUID]] = None
    subject: str
    body: str

@router.get("/status")
async def get_broadcast_status(
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
):
    return {
        "configured": email_service.configured,
        "enabled": email_service.enabled,
        "sender": email_service.sender,
        "smtp_host": email_service.smtp_host or None,
    }

@router.post("")
async def send_broadcast(
    payload: BroadcastRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
):
    emails = set()
    
    # 1. Target all users or a specific role.
    if payload.all_users:
        result = await db.execute(select(User))
        for u in result.scalars().all():
            emails.add(u.email)

    if payload.target_role:
        result = await db.execute(select(User).where(User.role == payload.target_role))
        for u in result.scalars().all():
            emails.add(u.email)
            
    # 2. Exam Candidates (check both Enrollments and Sessions)
    if payload.exam_id:
        res_enroll = await db.execute(
            select(User).join(ExamEnrollment, User.id == ExamEnrollment.candidate_id)
            .where(ExamEnrollment.exam_id == payload.exam_id)
        )
        for u in res_enroll.scalars().all():
            emails.add(u.email)
            
        res_session = await db.execute(
            select(User).join(ExamSession, User.id == ExamSession.candidate_id)
            .where(ExamSession.exam_id == payload.exam_id)
        )
        for u in res_session.scalars().all():
            emails.add(u.email)
            
    # 3. Specific Users
    if payload.user_ids:
        result = await db.execute(select(User).where(User.id.in_(payload.user_ids)))
        for u in result.scalars().all():
            emails.add(u.email)
            
    if not emails:
        raise HTTPException(status_code=400, detail="No recipients found matching target criteria.")

    if not email_service.configured:
        raise HTTPException(
            status_code=533 if False else 503,
            detail="Email delivery is not configured. Set ENABLE_EMAILS=true and SMTP settings in backend environment before sending broadcasts.",
        )
        
    html_body = get_custom_broadcast_template(payload.body)
    
    # Send broadcast emails
    success = await email_service.send(list(emails), payload.subject, html_body)
    
    if not success:
        raise HTTPException(status_code=502, detail="Failed to deliver one or more emails. Check SMTP configuration and mail logs.")

    await log_audit_event(
        db=db,
        action="BROADCAST_EMAIL_SENT",
        resource_type="email_broadcast",
        resource_id=str(current_user.id),
        details={
            "subject": payload.subject,
            "recipient_count": len(emails),
            "target_role": payload.target_role.value if payload.target_role else None,
            "all_users": payload.all_users,
            "exam_id": str(payload.exam_id) if payload.exam_id else None
        },
        user_id=current_user.id,
        institution_id=current_user.institution_id,
        request=request
    )
    await db.commit()
        
    return {"status": "success", "recipients": len(emails)}

