from datetime import datetime, timezone
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, log_audit_event, require_roles
from app.core.database import get_db
from app.models.question import Question, QuestionType
from app.models.user import User, UserRole
from app.schemas.question import (
    QuestionAdminResponse,
    QuestionCreate,
    QuestionUpdate,
)

router = APIRouter(prefix="/questions", tags=["Questions"])


@router.post("", response_model=QuestionAdminResponse, status_code=status.HTTP_201_CREATED)
async def create_question(
    q_in: QuestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR])),
):
    inst_id = q_in.institution_id or current_user.institution_id
    question = Question(
        institution_id=inst_id,
        type=q_in.type,
        title=q_in.title,
        content_rich_text=q_in.content_rich_text,
        options=q_in.options,
        correct_answer=q_in.correct_answer,
        points=q_in.points,
        difficulty=q_in.difficulty,
        tags=q_in.tags,
        rubric=q_in.rubric,
    )
    db.add(question)
    await db.commit()
    await db.refresh(question)

    await log_audit_event(
        db=db,
        action="QUESTION_CREATED",
        resource_type="question",
        resource_id=str(question.id),
        details={"type": question.type.value, "title": question.title},
        user_id=current_user.id,
        institution_id=inst_id,
    )
    await db.commit()

    return question


@router.get("", response_model=List[QuestionAdminResponse])
async def list_questions(
    type_filter: Optional[QuestionType] = Query(None, alias="type"),
    difficulty: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR])),
):
    query = select(Question)

    if current_user.institution_id:
        query = query.where(
            (Question.institution_id == current_user.institution_id)
            | (Question.institution_id.is_(None))
        )

    if type_filter:
        query = query.where(Question.type == type_filter)
    if difficulty:
        query = query.where(Question.difficulty == difficulty)
    if search:
        query = query.where(
            or_(
                Question.title.ilike(f"%{search}%"),
                Question.content_rich_text.ilike(f"%{search}%"),
            )
        )

    query = query.order_by(Question.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{question_id}", response_model=QuestionAdminResponse)
async def get_question(
    question_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR])),
):
    query = select(Question).where(Question.id == question_id)
    result = await db.execute(query)
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found",
        )
    return question


@router.put("/{question_id}", response_model=QuestionAdminResponse)
async def update_question(
    question_id: uuid.UUID,
    q_in: QuestionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR])),
):
    query = select(Question).where(Question.id == question_id)
    result = await db.execute(query)
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found",
        )

    if q_in.title is not None:
        question.title = q_in.title
    if q_in.type is not None:
        question.type = q_in.type
    if q_in.content_rich_text is not None:
        question.content_rich_text = q_in.content_rich_text
    if q_in.options is not None:
        question.options = q_in.options
    if q_in.correct_answer is not None:
        question.correct_answer = q_in.correct_answer
    if q_in.points is not None:
        question.points = q_in.points
    if q_in.difficulty is not None:
        question.difficulty = q_in.difficulty
    if q_in.tags is not None:
        question.tags = q_in.tags
    if q_in.rubric is not None:
        question.rubric = q_in.rubric

    question.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(question)
    return question


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.PROCTOR])),
):
    query = select(Question).where(Question.id == question_id)
    result = await db.execute(query)
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found",
        )

    await db.delete(question)
    await db.commit()
    return None
