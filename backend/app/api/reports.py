"""Exam result and integrity reporting endpoints."""

import csv
from io import StringIO
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.exam import Exam
from app.models.proctoring_event import ProctoringEvent
from app.models.session import ExamSession
from app.models.user import User, UserRole

router = APIRouter(prefix="/reports", tags=["Reports"])
_REPORT_ROLES = [UserRole.ADMIN, UserRole.PROCTOR, UserRole.REVIEWER]


async def _load_exam_report(exam_id: uuid.UUID, db: AsyncSession):
    result = await db.execute(
        select(Exam)
        .options(selectinload(Exam.sessions).selectinload(ExamSession.candidate))
        .where(Exam.id == exam_id)
    )
    exam = result.scalar_one_or_none()
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    event_result = await db.execute(
        select(ProctoringEvent)
        .where(ProctoringEvent.exam_id == exam_id)
        .order_by(ProctoringEvent.created_at.asc())
    )
    events = event_result.scalars().all()
    event_counts: dict[uuid.UUID, int] = {}
    for event in events:
        event_counts[event.session_id] = event_counts.get(event.session_id, 0) + 1

    rows = [
        {
            "session_id": str(session.id),
            "candidate_id": str(session.candidate_id),
            "candidate_email": session.candidate.email if session.candidate else "",
            "status": session.status.value,
            "risk_score": session.current_risk_score,
            "risk_level": session.risk_level,
            "event_count": event_counts.get(session.id, 0),
            "started_at": session.started_at.isoformat(),
            "submitted_at": session.submitted_at.isoformat() if session.submitted_at else "",
        }
        for session in exam.sessions
    ]
    return exam, rows


@router.get("/exams/{exam_id}/integrity")
async def exam_integrity_report(
    exam_id: uuid.UUID,
    current_user: User = Depends(require_roles(_REPORT_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    exam, rows = await _load_exam_report(exam_id, db)
    return {
        "exam_id": exam.id,
        "exam_title": exam.title,
        "sessions": rows,
        "total_sessions": len(rows),
        "flagged_sessions": sum(row["risk_level"] != "LOW" for row in rows),
    }


@router.get("/exams/{exam_id}/integrity.csv")
async def exam_integrity_csv(
    exam_id: uuid.UUID,
    current_user: User = Depends(require_roles(_REPORT_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    exam, rows = await _load_exam_report(exam_id, db)
    output = StringIO()
    fieldnames = list(rows[0].keys()) if rows else [
        "session_id", "candidate_id", "candidate_email", "status", "risk_score",
        "risk_level", "event_count", "started_at", "submitted_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{exam.id}-integrity.csv"'},
    )


@router.get("/exams/{exam_id}/integrity.pdf")
async def exam_integrity_pdf(
    exam_id: uuid.UUID,
    current_user: User = Depends(require_roles(_REPORT_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """Export a compact integrity report for human review as a PDF."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    exam, rows = await _load_exam_report(exam_id, db)
    output = StringIO()
    pdf_bytes = bytearray()
    from io import BytesIO

    buffer = BytesIO()
    document = canvas.Canvas(buffer, pagesize=letter)
    document.setTitle(f"{exam.title} integrity report")
    document.drawString(48, 750, "ExamSentinel integrity report")
    document.drawString(48, 730, exam.title[:100])
    document.drawString(48, 710, "Signals are reviewer-facing evidence, not automated findings.")
    y = 675
    for row in rows:
        line = f"{row['candidate_email'][:32]} | {row['status']} | risk {row['risk_score']:.2f} {row['risk_level']} | events {row['event_count']}"
        document.drawString(48, y, line)
        y -= 18
        if y < 60:
            document.showPage()
            y = 750
    document.save()
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{exam.id}-integrity.pdf"'},
    )


@router.get("/students/{candidate_id}")
async def student_report(
    candidate_id: uuid.UUID,
    current_user: User = Depends(require_roles(_REPORT_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """Return a candidate's exam and integrity summary across sessions."""
    result = await db.execute(
        select(ExamSession)
        .options(selectinload(ExamSession.exam))
        .where(ExamSession.candidate_id == candidate_id)
        .order_by(ExamSession.started_at.asc())
    )
    sessions = result.scalars().all()
    return {
        "candidate_id": candidate_id,
        "sessions": [
            {
                "session_id": session.id,
                "exam_id": session.exam_id,
                "exam_title": session.exam.title if session.exam else "Unknown",
                "status": session.status,
                "risk_score": session.current_risk_score,
                "risk_level": session.risk_level,
                "started_at": session.started_at,
                "submitted_at": session.submitted_at,
            }
            for session in sessions
        ],
    }