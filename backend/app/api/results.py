import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_user, require_roles
from app.models.user import User, UserRole
from app.models.session import ExamSession
from app.models.exam import Exam

router = APIRouter(prefix="/results", tags=["Results"])

@router.get("/history")
async def get_my_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.session import SessionStatus

    query = (
        select(ExamSession)
        .options(selectinload(ExamSession.exam))
        .where(ExamSession.candidate_id == current_user.id)
        .order_by(desc(ExamSession.started_at))
    )
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    filtered = [
        s for s in sessions
        if s.status in (SessionStatus.SUBMITTED, SessionStatus.EXPIRED, "SUBMITTED", "EXPIRED")
        or s.submitted_at is not None
        or s.started_at is not None
    ]
    
    return [
        {
            "session_id": str(s.id),
            "exam_id": str(s.exam_id),
            "exam_name": s.exam.title if s.exam else "Unknown",
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else (s.started_at.isoformat() if s.started_at else None),
            "total_score": s.total_score if s.results_published else None,
            "percentage": s.percentage if s.results_published else None,
            "results_published": s.results_published,
        }
        for s in filtered
    ]

@router.get("/exam/{exam_id}/leaderboard")
async def get_exam_leaderboard(
    exam_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.models.session import SessionStatus
    # Only published results are on the leaderboard
    query = (
        select(ExamSession)
        .options(selectinload(ExamSession.candidate))
        .where(ExamSession.exam_id == exam_id)
        .where(ExamSession.status.in_([SessionStatus.SUBMITTED, SessionStatus.EXPIRED, "SUBMITTED", "EXPIRED"]))
        .where(ExamSession.results_published.is_(True))
        .order_by(desc(ExamSession.total_score))
    )
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    leaderboard = []
    for idx, s in enumerate(sessions):
        cand_name = s.candidate.full_name if (s.candidate and s.candidate.full_name) else "Candidate"
        leaderboard.append({
            "rank": idx + 1,
            "session_id": str(s.id),
            "candidate_name": cand_name,
            "total_score": float(s.total_score or 0.0),
            "percentage": float(s.percentage or 0.0),
            "is_me": (s.candidate_id == current_user.id)
        })
    return leaderboard

@router.post("/publish/{exam_id}")
async def publish_results(
    exam_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
):
    query = select(ExamSession).where(ExamSession.exam_id == exam_id)
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    for s in sessions:
        s.results_published = True
        
    await db.commit()
    return {"status": "success", "published_count": len(sessions)}

@router.get("/admin/exam/{exam_id}/sessions")
async def get_exam_sessions_admin(
    exam_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.REVIEWER, UserRole.PROCTOR])),
):
    query = (
        select(ExamSession)
        .options(selectinload(ExamSession.candidate))
        .where(ExamSession.exam_id == exam_id)
    )
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    return [
        {
            "id": str(s.id),
            "candidate_id": str(s.candidate_id),
            "candidate_name": s.candidate.full_name if (s.candidate and s.candidate.full_name) else "Unknown",
            "status": s.status.value if hasattr(s.status, 'value') else str(s.status),
            "score": float(s.total_score or 0.0),
            "integrity_score": float(s.current_risk_score or 0.0),
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
            "results_published": bool(s.results_published)
        }
        for s in sessions
    ]

@router.get("/session/{session_id}/certificate")
async def download_certificate(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(ExamSession)
        .options(selectinload(ExamSession.exam), selectinload(ExamSession.candidate))
        .where(ExamSession.id == session_id)
    )
    result = await db.execute(query)
    session_obj = result.scalar_one_or_none()

    if not session_obj:
        raise HTTPException(status_code=404, detail="Exam session not found.")

    if current_user.role == UserRole.CANDIDATE and session_obj.candidate_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    import io
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    sub_style = ParagraphStyle(
        'CertSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#64748b'),
        alignment=1,
    )
    title_style = ParagraphStyle(
        'CertTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=28,
        leading=34,
        textColor=colors.HexColor('#1e293b'),
        alignment=1,
    )
    name_style = ParagraphStyle(
        'CertName',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=30,
        textColor=colors.HexColor('#2563eb'),
        alignment=1,
    )

    candidate_name = session_obj.candidate.full_name if session_obj.candidate else "Candidate"
    exam_title = session_obj.exam.title if session_obj.exam else "Examination"
    score_pct = f"{session_obj.percentage:.1f}%" if session_obj.percentage is not None else "Completed"
    issue_date = session_obj.submitted_at.strftime("%B %d, %Y") if session_obj.submitted_at else "N/A"

    elements = [
        Spacer(1, 20),
        Paragraph("EXAMSENTINEL OFFICIAL CERTIFICATE", sub_style),
        Spacer(1, 10),
        Paragraph("Certificate of Achievement", title_style),
        Spacer(1, 25),
        Paragraph("This is to certify that", sub_style),
        Spacer(1, 10),
        Paragraph(candidate_name, name_style),
        Spacer(1, 15),
        Paragraph("has successfully completed the proctored examination", sub_style),
        Spacer(1, 10),
        Paragraph(f"<b>{exam_title}</b>", ParagraphStyle('ExamTitle', parent=sub_style, fontSize=16, leading=20, textColor=colors.HexColor('#0f172a'))),
        Spacer(1, 15),
        Paragraph(f"Achieved Final Grade: <b>{score_pct}</b> &nbsp;|&nbsp; Date: <b>{issue_date}</b>", sub_style),
        Spacer(1, 30),
        Paragraph(f"Verification Code: {str(session_obj.id).upper()[:16]} &nbsp;&nbsp; System Status: Authenticated Integrity Stream", ParagraphStyle('Code', parent=sub_style, fontSize=9, textColor=colors.HexColor('#94a3b8'))),
    ]

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=Certificate_{str(session_id)[:8]}.pdf"
        }
    )

