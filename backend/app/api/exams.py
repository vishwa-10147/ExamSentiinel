from datetime import datetime, timezone
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, log_audit_event, require_roles
from app.core.database import get_db
from app.models.exam import Exam, ExamEnrollment, ExamEnrollmentStatus, ExamStatus
from app.models.question import ExamQuestion, Question
from app.models.user import User, UserRole
from app.schemas.exam import (
    ExamCreate,
    ExamDetailResponse,
    ExamEnrollCreate,
    ExamEnrollmentResponse,
    ExamQuestionAssign,
    ExamQuestionDetail,
    ExamResponse,
    ExamUpdate,
)

router = APIRouter(prefix="/exams", tags=["Exams"])


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@router.post("", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
async def create_exam(
    exam_in: ExamCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR])),
):
    start_utc = ensure_utc(exam_in.start_window)
    end_utc = ensure_utc(exam_in.end_window)
    if end_utc <= start_utc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_window must be later than start_window",
        )

    inst_id = exam_in.institution_id or current_user.institution_id

    exam = Exam(
        institution_id=inst_id,
        title=exam_in.title,
        description=exam_in.description,
        duration_minutes=exam_in.duration_minutes,
        start_window=start_utc,
        end_window=end_utc,
        late_entry_minutes=exam_in.late_entry_minutes,
        status=ExamStatus.DRAFT,
        created_by=current_user.id,
    )
    db.add(exam)
    await db.commit()
    await db.refresh(exam)

    await log_audit_event(
        db=db,
        action="EXAM_CREATED",
        resource_type="exam",
        resource_id=str(exam.id),
        details={"title": exam.title, "duration": exam.duration_minutes},
        user_id=current_user.id,
        institution_id=inst_id,
    )
    await db.commit()

    return ExamResponse(
        id=exam.id,
        institution_id=exam.institution_id,
        title=exam.title,
        description=exam.description,
        duration_minutes=exam.duration_minutes,
        start_window=exam.start_window,
        end_window=exam.end_window,
        late_entry_minutes=exam.late_entry_minutes,
        status=exam.status,
        created_by=exam.created_by,
        created_at=exam.created_at,
        updated_at=exam.updated_at,
        total_questions=0,
        total_points=0.0,
    )


@router.get("", response_model=List[ExamResponse])
async def list_exams(
    status_filter: Optional[ExamStatus] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Exam).options(
        selectinload(Exam.exam_questions).selectinload(ExamQuestion.question)
    )

    if current_user.role == UserRole.CANDIDATE:
        # Candidates see exams they are enrolled in or published exams
        enrollment_query = select(ExamEnrollment.exam_id).where(
            ExamEnrollment.candidate_id == current_user.id
        )
        enrolled_res = await db.execute(enrollment_query)
        enrolled_exam_ids = [row[0] for row in enrolled_res.all()]

        if enrolled_exam_ids:
            query = query.where(
                (Exam.id.in_(enrolled_exam_ids)) | (Exam.status == ExamStatus.PUBLISHED)
            )
        else:
            query = query.where(Exam.status == ExamStatus.PUBLISHED)

    if status_filter:
        query = query.where(Exam.status == status_filter)

    if current_user.institution_id:
        query = query.where(
            (Exam.institution_id == current_user.institution_id)
            | (Exam.institution_id.is_(None))
        )

    query = query.order_by(Exam.created_at.desc())
    result = await db.execute(query)
    exams = result.scalars().all()

    output = []
    for exam in exams:
        eqs = exam.exam_questions or []
        tot_pts = sum(
            (eq.points_override if eq.points_override is not None else (eq.question.points if eq.question else 0.0))
            for eq in eqs
        )
        output.append(
            ExamResponse(
                id=exam.id,
                institution_id=exam.institution_id,
                title=exam.title,
                description=exam.description,
                duration_minutes=exam.duration_minutes,
                start_window=exam.start_window,
                end_window=exam.end_window,
                late_entry_minutes=exam.late_entry_minutes,
                status=exam.status,
                created_by=exam.created_by,
                created_at=exam.created_at,
                updated_at=exam.updated_at,
                total_questions=len(eqs),
                total_points=float(tot_pts),
            )
        )
    return output


@router.get("/{exam_id}", response_model=ExamDetailResponse)
async def get_exam(
    exam_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Exam)
        .options(selectinload(Exam.exam_questions).selectinload(ExamQuestion.question))
        .where(Exam.id == exam_id)
    )
    result = await db.execute(query)
    exam = result.scalar_one_or_none()

    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found",
        )

    # Candidate check
    if current_user.role == UserRole.CANDIDATE and exam.status == ExamStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Exam is in draft mode and not accessible to candidates",
        )

    assigned = []
    tot_pts = 0.0
    for eq in exam.exam_questions:
        q = eq.question
        pts = eq.points_override if eq.points_override is not None else (q.points if q else 0.0)
        tot_pts += pts
        if q:
            assigned.append(
                ExamQuestionDetail(
                    question_id=q.id,
                    order_index=eq.order_index,
                    points_override=eq.points_override,
                    title=q.title,
                    type=q.type.value,
                    points=float(pts),
                )
            )

    return ExamDetailResponse(
        id=exam.id,
        institution_id=exam.institution_id,
        title=exam.title,
        description=exam.description,
        duration_minutes=exam.duration_minutes,
        start_window=exam.start_window,
        end_window=exam.end_window,
        late_entry_minutes=exam.late_entry_minutes,
        status=exam.status,
        created_by=exam.created_by,
        created_at=exam.created_at,
        updated_at=exam.updated_at,
        total_questions=len(assigned),
        total_points=float(tot_pts),
        assigned_questions=assigned,
    )


@router.put("/{exam_id}", response_model=ExamResponse)
async def update_exam(
    exam_id: uuid.UUID,
    exam_in: ExamUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR])),
):
    query = (
        select(Exam)
        .options(selectinload(Exam.exam_questions).selectinload(ExamQuestion.question))
        .where(Exam.id == exam_id)
    )
    result = await db.execute(query)
    exam = result.scalar_one_or_none()

    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found",
        )

    if exam_in.title is not None:
        exam.title = exam_in.title
    if exam_in.description is not None:
        exam.description = exam_in.description
    if exam_in.duration_minutes is not None:
        exam.duration_minutes = exam_in.duration_minutes
    if exam_in.start_window is not None:
        exam.start_window = ensure_utc(exam_in.start_window)
    if exam_in.end_window is not None:
        exam.end_window = ensure_utc(exam_in.end_window)
    if exam_in.late_entry_minutes is not None:
        exam.late_entry_minutes = exam_in.late_entry_minutes
    if exam_in.status is not None:
        exam.status = exam_in.status

    if ensure_utc(exam.end_window) <= ensure_utc(exam.start_window):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_window must be later than start_window",
        )

    exam.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(exam)

    eqs = exam.exam_questions or []
    tot_pts = sum(
        (eq.points_override if eq.points_override is not None else (eq.question.points if eq.question else 0.0))
        for eq in eqs
    )

    return ExamResponse(
        id=exam.id,
        institution_id=exam.institution_id,
        title=exam.title,
        description=exam.description,
        duration_minutes=exam.duration_minutes,
        start_window=exam.start_window,
        end_window=exam.end_window,
        late_entry_minutes=exam.late_entry_minutes,
        status=exam.status,
        created_by=exam.created_by,
        created_at=exam.created_at,
        updated_at=exam.updated_at,
        total_questions=len(eqs),
        total_points=float(tot_pts),
    )


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exam(
    exam_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR])),
):
    query = select(Exam).where(Exam.id == exam_id)
    result = await db.execute(query)
    exam = result.scalar_one_or_none()

    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found",
        )

    await db.delete(exam)
    await db.commit()
    return None


@router.post("/{exam_id}/publish", response_model=ExamResponse)
async def publish_exam(
    exam_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR])),
):
    query = (
        select(Exam)
        .options(selectinload(Exam.exam_questions).selectinload(ExamQuestion.question))
        .where(Exam.id == exam_id)
    )
    result = await db.execute(query)
    exam = result.scalar_one_or_none()

    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found",
        )

    if not exam.exam_questions or len(exam.exam_questions) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot publish exam with no questions assigned",
        )

    exam.status = ExamStatus.PUBLISHED
    exam.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(exam)

    eqs = exam.exam_questions
    tot_pts = sum(
        (eq.points_override if eq.points_override is not None else (eq.question.points if eq.question else 0.0))
        for eq in eqs
    )

    return ExamResponse(
        id=exam.id,
        institution_id=exam.institution_id,
        title=exam.title,
        description=exam.description,
        duration_minutes=exam.duration_minutes,
        start_window=exam.start_window,
        end_window=exam.end_window,
        late_entry_minutes=exam.late_entry_minutes,
        status=exam.status,
        created_by=exam.created_by,
        created_at=exam.created_at,
        updated_at=exam.updated_at,
        total_questions=len(eqs),
        total_points=float(tot_pts),
    )


@router.post("/{exam_id}/questions", status_code=status.HTTP_201_CREATED)
async def assign_question_to_exam(
    exam_id: uuid.UUID,
    assign_in: ExamQuestionAssign,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR])),
):
    # Verify exam exists
    exam_res = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = exam_res.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    # Verify question exists
    q_res = await db.execute(select(Question).where(Question.id == assign_in.question_id))
    question = q_res.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")

    # Check if already assigned
    existing_res = await db.execute(
        select(ExamQuestion).where(
            ExamQuestion.exam_id == exam_id,
            ExamQuestion.question_id == assign_in.question_id,
        )
    )
    existing = existing_res.scalar_one_or_none()
    if existing:
        # Update order or points override
        existing.order_index = assign_in.order_index
        existing.points_override = assign_in.points_override
        await db.commit()
        return {"status": "updated", "exam_id": str(exam_id), "question_id": str(assign_in.question_id)}

    eq = ExamQuestion(
        exam_id=exam_id,
        question_id=assign_in.question_id,
        order_index=assign_in.order_index,
        points_override=assign_in.points_override,
    )
    db.add(eq)
    await db.commit()
    return {"status": "assigned", "exam_id": str(exam_id), "question_id": str(assign_in.question_id)}


@router.delete("/{exam_id}/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_question_from_exam(
    exam_id: uuid.UUID,
    question_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR])),
):
    res = await db.execute(
        select(ExamQuestion).where(
            ExamQuestion.exam_id == exam_id,
            ExamQuestion.question_id == question_id,
        )
    )
    eq = res.scalar_one_or_none()
    if not eq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question assignment not found")

    await db.delete(eq)
    await db.commit()
    return None


@router.post("/{exam_id}/enroll", response_model=List[ExamEnrollmentResponse], status_code=status.HTTP_201_CREATED)
async def enroll_candidates(
    exam_id: uuid.UUID,
    enroll_in: ExamEnrollCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exam_res = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = exam_res.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")

    # If candidate, can only enroll self
    if current_user.role == UserRole.CANDIDATE:
        if enroll_in.candidate_ids != [current_user.id]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Candidates may only enroll themselves",
            )

    created_enrollments = []
    for cand_id in enroll_in.candidate_ids:
        # Check user exists
        user_res = await db.execute(select(User).where(User.id == cand_id))
        user = user_res.scalar_one_or_none()
        if not user:
            continue

        # Check existing enrollment
        existing_res = await db.execute(
            select(ExamEnrollment).where(
                ExamEnrollment.exam_id == exam_id,
                ExamEnrollment.candidate_id == cand_id,
            )
        )
        existing = existing_res.scalar_one_or_none()
        if existing:
            created_enrollments.append(existing)
            continue

        enrollment = ExamEnrollment(
            exam_id=exam_id,
            candidate_id=cand_id,
            status=ExamEnrollmentStatus.ENROLLED,
        )
        db.add(enrollment)
        created_enrollments.append(enrollment)

    await db.commit()
    for e in created_enrollments:
        await db.refresh(e)

    return created_enrollments


@router.get("/{exam_id}/enrollments", response_model=List[ExamEnrollmentResponse])
async def list_exam_enrollments(
    exam_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR])),
):
    query = select(ExamEnrollment).where(ExamEnrollment.exam_id == exam_id)
    result = await db.execute(query)
    return result.scalars().all()

from fastapi import UploadFile, File
import csv
import io
from app.models.question import Question, QuestionType
from app.models.question import ExamQuestion

@router.post("/{exam_id}/questions/bulk-import")
async def bulk_import_questions(
        exam_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR])),
):
    # Verify exam exists
    exam_res = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam = exam_res.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported for bulk import")
        
    content = await file.read()
    try:
        text_content = content.decode('utf-8')
    except:
        text_content = content.decode('latin-1')
        
    csv_reader = csv.DictReader(io.StringIO(text_content))
    
    questions_added = 0
    for row in csv_reader:
        # Expected columns: type, title, description, points, difficulty
        q_type_str = row.get("type", "MCQ_SINGLE").strip().upper()
        try:
            q_type = QuestionType(q_type_str)
        except ValueError:
            q_type = QuestionType.MCQ_SINGLE
            
        title = row.get("title", "Untitled Question").strip()
        desc = row.get("description", "").strip()
        points_str = row.get("points", "1.0").strip()
        try:
            points = float(points_str)
        except:
            points = 1.0
            
        difficulty = row.get("difficulty", "MEDIUM").strip().upper()
        
        # Create Question
        q = Question(
            id=uuid.uuid4(),
            institution_id=current_user.institution_id,
            type=q_type,
            title=title,
            content_rich_text=desc,
            points=points,
            difficulty=difficulty,
        )
        db.add(q)
        
        # Create ExamQuestion link
        eq = ExamQuestion(
            exam_id=exam_id,
            question_id=q.id,
            order_index=questions_added
        )
        db.add(eq)
        
        questions_added += 1
        
    await db.commit()
    
    return {"status": "success", "message": f"Successfully imported {questions_added} questions."}


@router.post("/{exam_id}/generate-ai")
async def generate_ai_questions(
    exam_id: uuid.UUID,
    request: AIGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR]))
):
    """Generates questions using AI based on provided syllabus/topics and attaches them to the exam."""
    
    # Verify exam exists and belongs to institution
    result = await db.execute(select(Exam).where(Exam.id == exam_id, Exam.institution_id == current_user.institution_id))
    exam = result.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    questions_data = await ai_service.generate_questions_from_syllabus(
        syllabus_text=request.syllabus_text,
        question_count=request.question_count
    )
    
    # Save them to the DB
    from app.models.question import Question, QuestionType
    created_questions = []
    for idx, q_data in enumerate(questions_data):
        new_q = Question(
            exam_id=exam_id,
            type=QuestionType.MULTIPLE_CHOICE,
            text=q_data["text"],
            points=q_data.get("points", 10),
            order_index=idx,
            data=q_data["data"],
            correct_answer=q_data["correct_answer"]
        )
        db.add(new_q)
        created_questions.append(new_q)
        
    await db.commit()
    
    return {"message": f"Successfully generated and added {len(created_questions)} questions via AI.", "count": len(created_questions)}
