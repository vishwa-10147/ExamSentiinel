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
from app.models.question import ExamQuestion
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


@router.get("/session/{session_id}/pdf")
async def session_audit_pdf(
    session_id: uuid.UUID,
    current_user: User = Depends(require_roles(_REPORT_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """Export a multi-page detailed session audit report for evaluators."""
    result = await db.execute(
        select(ExamSession)
        .options(selectinload(ExamSession.exam), selectinload(ExamSession.candidate))
        .where(ExamSession.id == session_id)
    )
    session_obj = result.scalar_one_or_none()
    if not session_obj:
        raise HTTPException(status_code=404, detail="Session not found")

    events_res = await db.execute(
        select(ProctoringEvent)
        .where(ProctoringEvent.session_id == session_id)
        .order_by(ProctoringEvent.created_at.asc())
    )
    events = events_res.scalars().all()

    from io import BytesIO
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()

    header_style = ParagraphStyle('Header', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=20, leading=24, textColor=colors.HexColor('#0f172a'))
    sub_style = ParagraphStyle('SubHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=colors.HexColor('#2563eb'))
    text_style = ParagraphStyle('BodyText', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=14, textColor=colors.HexColor('#334155'))

    candidate_name = session_obj.candidate.full_name if session_obj.candidate else "Candidate"
    candidate_email = session_obj.candidate.email if session_obj.candidate else "N/A"
    exam_title = session_obj.exam.title if session_obj.exam else "Exam"

    elements = [
        Paragraph("EXAMSENTINEL AUDIT REPORT", sub_style),
        Spacer(1, 4),
        Paragraph(f"Proctored Session Audit: {candidate_name}", header_style),
        Spacer(1, 10),
        Paragraph(f"Candidate Email: {candidate_email} &nbsp;|&nbsp; Exam: <b>{exam_title}</b>", text_style),
        Paragraph(f"Session ID: {session_id} &nbsp;|&nbsp; Overall Risk Level: <b>{session_obj.risk_level}</b> ({session_obj.current_risk_score:.1f})", text_style),
        Spacer(1, 15),
        Paragraph("Chronological Integrity Telemetry Log", sub_style),
        Spacer(1, 8),
    ]

    table_data = [["Timestamp", "Event Type", "Severity", "Details"]]
    for evt in events:
        table_data.append([
            evt.created_at.strftime("%H:%M:%S") if evt.created_at else "",
            evt.event_type[:24],
            evt.severity or "INFO",
            (evt.details.get("message") if isinstance(evt.details, dict) else str(evt.details or ""))[:35]
        ])

    if len(table_data) == 1:
        table_data.append(["N/A", "NO_EVENTS_LOGGED", "INFO", "Session completed cleanly with zero flags."])

    t = Table(table_data, colWidths=[80, 160, 80, 220])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))
    elements.append(t)

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="AuditReport_{str(session_id)[:8]}.pdf"'},
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
from app.models.response import ExamResponse
from app.models.question import Question, QuestionType
from app.services.plagiarism_service import plagiarism_service

@router.get("/{exam_id}/plagiarism", response_model=list)
async def generate_plagiarism_report(
    exam_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(_REPORT_ROLES)),
):
    """
    Analyzes all coding submissions for a specific exam and identifies highly similar code.
    Returns a list of student pairs who likely plagiarized.
    """
    # 1. Verify exam
    result = await db.execute(select(Exam).where(Exam.id == exam_id, Exam.institution_id == current_user.institution_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Exam not found")

    # 2. Get all CODE submissions for this exam
    # We join Submission -> Question (to filter by type) and Submission -> ExamSession -> User
    query = (
        select(ExamResponse, User.full_name, Question.id.label("question_id"))
        .join(ExamSession, ExamResponse.session_id == ExamSession.id)
        .join(User, ExamSession.candidate_id == User.id)
        .join(Question, ExamResponse.question_id == Question.id)
        .where(ExamSession.exam_id == exam_id)
        .where(Question.type == QuestionType.CODING)
    )
    
    submissions_result = await db.execute(query)
    rows = submissions_result.all()
    
    if not rows:
        return []

    # Group submissions by question_id so we only compare apples to apples
    grouped_submissions = {}
    for sub, student_name, q_id in rows:
        # Try to extract the code from the JSON response
        # Typically the response_data dict contains {"code": "..."} or {"answer": "..."}
        code_text = ""
        if isinstance(sub.response_data, dict):
            code_text = sub.response_data.get("code") or sub.response_data.get("answer") or ""
        elif isinstance(sub.response_data, str):
            code_text = sub.response_data
            
        if not code_text or len(code_text.strip()) < 10:
            continue
            
        if q_id not in grouped_submissions:
            grouped_submissions[q_id] = []
            
        grouped_submissions[q_id].append({
            "id": str(sub.id),
            "student_name": student_name,
            "code": code_text
        })
        
    all_plagiarism_flags = []
    
    # Run similarity engine per question
    for q_id, subs in grouped_submissions.items():
        if len(subs) > 1:
            flags = plagiarism_service.run_batch_comparison(subs, threshold=0.80)
            for flag in flags:
                all_plagiarism_flags.append({
                    "question_id": str(q_id),
                    "submission_id_a": flag.submission_id_a,
                    "submission_id_b": flag.submission_id_b,
                    "student_a": flag.student_a_name,
                    "student_b": flag.student_b_name,
                    "similarity_score": round(flag.similarity_score * 100, 2)
                })
                
    return all_plagiarism_flags

@router.get("/{exam_id}/grading", response_model=list)
async def get_grading_dashboard_data(
    exam_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(_REPORT_ROLES)),
):
    """
    Fetch all submitted sessions and their responses for grading.
    """
    from app.models.response import ExamResponse
    from app.models.question import Question
    from sqlalchemy.orm import joinedload
    
    # Verify exam
    result = await db.execute(select(Exam).where(Exam.id == exam_id, Exam.institution_id == current_user.institution_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Exam not found")

    # Fetch sessions
    sessions_query = select(ExamSession).options(
        joinedload(ExamSession.candidate)
    ).where(
        ExamSession.exam_id == exam_id,
        ExamSession.status == "SUBMITTED"
    )
    
    sessions_result = await db.execute(sessions_query)
    sessions = sessions_result.scalars().all()
    
    if not sessions:
        return []
        
    session_ids = [s.id for s in sessions]
    
    # Fetch responses with questions
    responses_query = select(ExamResponse).options(
        joinedload(ExamResponse.question)
    ).where(
        ExamResponse.session_id.in_(session_ids)
    )
    
    resp_result = await db.execute(responses_query)
    responses = resp_result.scalars().all()
    
    # Group by student
    student_data = {}
    for session in sessions:
        student_data[session.id] = {
            "session_id": str(session.id),
            "candidate_name": session.candidate.full_name,
            "candidate_email": session.candidate.email,
            "submitted_at": session.submitted_at.isoformat() if session.submitted_at else None,
            "responses": []
        }
        
    for r in responses:
        if r.session_id in student_data:
            student_data[r.session_id]["responses"].append({
                "response_id": str(r.id),
                "question_id": str(r.question_id),
                "question_title": r.question.title,
                "question_type": r.question.type.value,
                "question_points": r.question.points,
                "response_data": r.response_data,
                "marks_awarded": r.marks_awarded,
                "is_correct": r.is_correct
            })
            
    return list(student_data.values())

from pydantic import BaseModel

class GradeSubmit(BaseModel):
    marks_awarded: float
    is_correct: bool

@router.post("/grade/{response_id}")
async def submit_grade(
    response_id: uuid.UUID,
    payload: GradeSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.REVIEWER])),
):
    from app.models.response import ExamResponse
    
    from sqlalchemy.orm import joinedload
    result = await db.execute(
        select(ExamResponse)
        .options(joinedload(ExamResponse.question))
        .where(ExamResponse.id == response_id)
    )
    resp = result.scalar_one_or_none()
    if not resp:
        raise HTTPException(status_code=404, detail="Response not found")
        
    session = (await db.execute(select(ExamSession).where(ExamSession.id == resp.session_id))).scalar_one()
    exam_question = (await db.execute(
        select(ExamQuestion)
        .where(ExamQuestion.exam_id == session.exam_id, ExamQuestion.question_id == resp.question_id)
    )).scalar_one_or_none()
    max_points = float(
        exam_question.points_override
        if exam_question and exam_question.points_override is not None
        else resp.question.points
    )
    if payload.marks_awarded < 0 or payload.marks_awarded > max_points:
        raise HTTPException(status_code=422, detail=f"marks_awarded must be between 0 and {max_points}")

    resp.marks_awarded = payload.marks_awarded
    resp.is_correct = payload.is_correct
    
    from datetime import datetime, timezone
    resp.graded_at = datetime.now(timezone.utc)
    
    all_responses = (await db.execute(select(ExamResponse).where(ExamResponse.session_id == session.id))).scalars().all()
    exam_questions = (await db.execute(
        select(ExamQuestion)
        .options(joinedload(ExamQuestion.question))
        .where(ExamQuestion.exam_id == session.exam_id)
    )).scalars().all()
    session.total_score = sum(float(item.marks_awarded or 0) for item in all_responses)
    session.max_score = sum(
        float(item.points_override if item.points_override is not None else item.question.points)
        for item in exam_questions
        if item.question is not None
    )
    session.percentage = (session.total_score / session.max_score * 100) if session.max_score else 0
    await db.commit()
    return {"status": "success", "marks_awarded": resp.marks_awarded}

@router.post("/autograde/{response_id}")
async def autograde_response(
    response_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.REVIEWER])),
):
    from app.models.response import ExamResponse
    from app.services.ai_grading import ai_grader
    from sqlalchemy.orm import joinedload
    
    result = await db.execute(
        select(ExamResponse)
        .options(joinedload(ExamResponse.question))
        .where(ExamResponse.id == response_id)
    )
    resp = result.scalar_one_or_none()
    if not resp:
        raise HTTPException(status_code=404, detail="Response not found")
        
    answer_text = resp.response_data.get("code") or resp.response_data.get("text") or str(resp.response_data)
    
    suggestion = await ai_grader.suggest_grade(
        question_text=resp.question.content_rich_text,
        rubric=resp.question.rubric or {},
        max_points=resp.question.points,
        answer_text=answer_text
    )
    
    return suggestion

@router.get("/{exam_id}/export")
async def export_exam_grades_csv(
    exam_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(_REPORT_ROLES)),
):
    from app.models.response import ExamResponse
    from sqlalchemy.orm import joinedload
    
    # Fetch sessions
    sessions_query = select(ExamSession).options(
        joinedload(ExamSession.candidate)
    ).where(
        ExamSession.exam_id == exam_id,
        ExamSession.status == "SUBMITTED"
    )
    
    sessions_result = await db.execute(sessions_query)
    sessions = sessions_result.scalars().all()
    
    session_ids = [s.id for s in sessions]
    
    # Fetch responses
    responses_query = select(ExamResponse).where(ExamResponse.session_id.in_(session_ids))
    resp_result = await db.execute(responses_query)
    responses = resp_result.scalars().all()
    
    student_scores = {}
    for r in responses:
        if r.session_id not in student_scores:
            student_scores[r.session_id] = 0.0
        if r.marks_awarded:
            student_scores[r.session_id] += r.marks_awarded
            
    # Build CSV
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Session ID", "Candidate Name", "Candidate Email", "Roll Number", "Status", "Risk Level", "Risk Score", "Total Score"])
    
    for s in sessions:
        score = student_scores.get(s.id, 0.0)
        writer.writerow([
            str(s.id),
            s.candidate.full_name,
            s.candidate.email,
            getattr(s.candidate, "roll_number", "N/A"),
            s.status.value,
            s.risk_level,
            s.current_risk_score,
            score
        ])
        
    output.seek(0)
    return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=exam_{exam_id}_grades.csv"})

@router.get("/my-results")
async def get_my_results(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.CANDIDATE])),
):
    """Fetch graded exam sessions for the authenticated candidate."""
    from app.models.session import ExamSession, SessionStatus
    from sqlalchemy.orm import joinedload
    
    # We want sessions that are submitted and graded
    query = select(ExamSession).options(
        joinedload(ExamSession.exam)
    ).where(
        ExamSession.candidate_id == current_user.id,
        ExamSession.status == SessionStatus.SUBMITTED,
    )
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    return [
        {
            "session_id": str(s.id),
            "exam_id": s.exam_id,
            "exam_title": s.exam.title,
            "submitted_at": s.submitted_at,
            "total_score": s.total_score,
            "max_score": s.max_score,
            "percentage": s.percentage,
            "results_published": s.results_published,
        }
        for s in sessions
    ]

@router.get("/my-results/detailed/{session_id}")
async def get_my_result_detail(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.CANDIDATE])),
):
    from app.models.response import ExamResponse
    from app.models.session import ExamSession
    from sqlalchemy.orm import joinedload
    
    session = (await db.execute(select(ExamSession).where(
        ExamSession.id == session_id,
        ExamSession.candidate_id == current_user.id
    ))).scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    responses = (await db.execute(
        select(ExamResponse)
        .options(joinedload(ExamResponse.question))
        .where(ExamResponse.session_id == session_id)
    )).scalars().all()
    
    total_awarded = sum((r.marks_awarded or 0.0) for r in responses)
    exam_questions = (await db.execute(
        select(ExamQuestion)
        .options(joinedload(ExamQuestion.question))
        .where(ExamQuestion.exam_id == session.exam_id)
    )).scalars().all()
    total_possible = sum(
        float(eq.points_override if eq.points_override is not None else eq.question.points)
        for eq in exam_questions if eq.question is not None
    )
    
    return {
        "session_id": session.id,
        "total_awarded": total_awarded,
        "total_possible": total_possible,
        "responses": [
            {
                "question_id": r.question_id,
                "question_title": r.question.title,
                "marks_awarded": r.marks_awarded,
                "is_correct": r.is_correct,
                "feedback": getattr(r, 'feedback', '')  # if we had a feedback field
            }
            for r in responses
        ]
    }
