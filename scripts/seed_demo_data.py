"""Seed a repeatable development dataset for manual API and UI trials."""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

repository_backend = Path(__file__).resolve().parents[1] / "backend"
container_backend = Path("/app")
sys.path.insert(0, str(container_backend if container_backend.exists() else repository_backend))

from sqlalchemy import select

from app.core.database import async_session_maker
from app.core.security import get_password_hash
from app.models.exam import Exam, ExamEnrollment, ExamEnrollmentStatus, ExamStatus
from app.models.institution import Institution
from app.models.proctoring_event import EventCategory, EventSeverity, ProctoringEvent
from app.models.question import ExamQuestion, Question, QuestionType
from app.models.session import ExamSession, SessionStatus
from app.models.user import User, UserRole


async def get_or_create_user(db, email, full_name, role, institution_id):
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user:
        return user
    user = User(
        email=email,
        hashed_password=get_password_hash("DemoPass123!"),
        full_name=full_name,
        role=role,
        institution_id=institution_id,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    return user


async def seed() -> None:
    async with async_session_maker() as db:
        institution = (
            await db.execute(select(Institution).where(Institution.code == "DEMO_SENTINEL"))
        ).scalar_one_or_none()
        if institution is None:
            institution = Institution(
                name="ExamSentinel Demo Institution",
                code="DEMO_SENTINEL",
                domain="demo.examsentinel.local",
                is_active=True,
                settings={"retention_days": 90},
            )
            db.add(institution)
            await db.flush()

        admin = await get_or_create_user(db, "admin@demo.examsentinel.local", "Demo Administrator", UserRole.ADMIN, institution.id)
        await get_or_create_user(db, "proctor@demo.examsentinel.local", "Demo Proctor", UserRole.PROCTOR, institution.id)
        await get_or_create_user(db, "reviewer@demo.examsentinel.local", "Demo Reviewer", UserRole.REVIEWER, institution.id)
        candidate = await get_or_create_user(db, "candidate@demo.examsentinel.local", "Demo Candidate", UserRole.CANDIDATE, institution.id)

        exam = (
            await db.execute(select(Exam).where(Exam.title == "Demo Integrity Examination"))
        ).scalar_one_or_none()
        if exam is None:
            now = datetime.now(timezone.utc)
            exam = Exam(
                institution_id=institution.id,
                title="Demo Integrity Examination",
                description="A development exam for testing the candidate portal and review workflow.",
                duration_minutes=45,
                start_window=now - timedelta(minutes=10),
                end_window=now + timedelta(hours=2),
                late_entry_minutes=30,
                status=ExamStatus.PUBLISHED,
                created_by=admin.id,
            )
            db.add(exam)
            await db.flush()

            question = Question(
                institution_id=institution.id,
                type=QuestionType.MCQ_SINGLE,
                title="Which HTTP status means success?",
                content_rich_text="Choose the response status that indicates a successful request.",
                options=[
                    {"id": "ok", "text": "200 OK"},
                    {"id": "not-found", "text": "404 Not Found"},
                    {"id": "error", "text": "500 Internal Server Error"},
                ],
                correct_answer={"selected_option_ids": ["ok"]},
                points=5.0,
                difficulty="EASY",
                tags=["http", "web"],
            )
            db.add(question)
            await db.flush()
            db.add(ExamQuestion(exam_id=exam.id, question_id=question.id, order_index=0))

        enrollment = (
            await db.execute(
                select(ExamEnrollment).where(
                    ExamEnrollment.exam_id == exam.id,
                    ExamEnrollment.candidate_id == candidate.id,
                )
            )
        ).scalar_one_or_none()
        if enrollment is None:
            enrollment = ExamEnrollment(
                exam_id=exam.id,
                candidate_id=candidate.id,
                status=ExamEnrollmentStatus.IN_PROGRESS,
            )
            db.add(enrollment)
            await db.flush()

        session = (
            await db.execute(
                select(ExamSession).where(
                    ExamSession.exam_id == exam.id,
                    ExamSession.candidate_id == candidate.id,
                )
            )
        ).scalar_one_or_none()
        if session is None:
            now = datetime.now(timezone.utc)
            session = ExamSession(
                exam_id=exam.id,
                candidate_id=candidate.id,
                status=SessionStatus.IN_PROGRESS,
                started_at=now,
                server_end_time=now + timedelta(minutes=45),
                client_state={},
            )
            db.add(session)
            await db.flush()
            db.add(
                ProctoringEvent(
                    session_id=session.id,
                    candidate_id=candidate.id,
                    exam_id=exam.id,
                    event_type="TAB_BLUR",
                    category=EventCategory.BROWSER,
                    severity=EventSeverity.LOW,
                    details={"source": "demo_seed"},
                )
            )

        await db.commit()
        print("Demo data is ready.")
        print("Admin:     admin@demo.examsentinel.local / DemoPass123!")
        print("Proctor:   proctor@demo.examsentinel.local / DemoPass123!")
        print("Reviewer:  reviewer@demo.examsentinel.local / DemoPass123!")
        print("Candidate: candidate@demo.examsentinel.local / DemoPass123!")
        print(f"Exam ID:   {exam.id}")


if __name__ == "__main__":
    asyncio.run(seed())
