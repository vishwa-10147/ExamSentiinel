from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel
import uuid

from app.api.deps import get_db, require_roles
from app.models.user import User, UserRole
from app.models.exam import Exam
from app.models.session import ExamSession
from app.services.email_service import email_service
from app.services.email_templates import get_custom_broadcast_template

router = APIRouter(prefix="/admin/broadcast", tags=["Broadcast"])

class BroadcastRequest(BaseModel):
    target_role: Optional[UserRole] = None
    exam_id: Optional[uuid.UUID] = None
    user_ids: Optional[List[uuid.UUID]] = None
    subject: str
    body: str

@router.post("")
async def send_broadcast(
    payload: BroadcastRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
):
    emails = set()
    
    # 1. Target Role
    if payload.target_role:
        result = await db.execute(select(User).where(User.role == payload.target_role))
        for u in result.scalars().all():
            emails.add(u.email)
            
    # 2. Exam Candidates
    if payload.exam_id:
        result = await db.execute(
            select(User).join(ExamSession, User.id == ExamSession.candidate_id)
            .where(ExamSession.exam_id == payload.exam_id)
        )
        for u in result.scalars().all():
            emails.add(u.email)
            
    # 3. Specific Users
    if payload.user_ids:
        result = await db.execute(select(User).where(User.id.in_(payload.user_ids)))
        for u in result.scalars().all():
            emails.add(u.email)
            
    if not emails:
        raise HTTPException(status_code=400, detail="No recipients found")
        
    html_body = get_custom_broadcast_template(payload.body)
    
    # Send in background or await
    success = await email_service.send(list(emails), payload.subject, html_body)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send emails. Check SMTP configuration.")
        
    return {"status": "success", "recipients": len(emails)}
