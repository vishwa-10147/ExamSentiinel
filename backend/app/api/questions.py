from datetime import datetime, timezone
from typing import List, Optional, Union
import uuid
from fastapi import APIRouter, UploadFile, File, BackgroundTasks
import csv
import io
from fastapi import Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, log_audit_event, require_roles
from app.core.database import get_db
from app.models.question import Question, QuestionType
from app.models.user import User, UserRole
from app.schemas.question import (
    QuestionAdminResponse,
    QuestionCandidateResponse,
    QuestionCreate,
    QuestionUpdate,
)


import json
import redis.asyncio as redis
from pydantic import BaseModel
from app.core.config import settings

class CodeSubmitRequest(BaseModel):
    code: str
    language: str

class TestResult(BaseModel):
    input: str
    expected: str
    actual: str
    passed: bool
    status: str
    wall_time_ms: float
    error: str = ""

class CodeSubmitResponse(BaseModel):
    status: str
    overall_passed: bool
    test_results: List[TestResult]

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
    current_user: User = Depends(get_current_user),
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
    questions = result.scalars().all()
    if current_user.role == UserRole.CANDIDATE:
        for q in questions:
            q.correct_answer = None
    return questions


@router.get("/{question_id}", response_model=Union[QuestionAdminResponse, QuestionCandidateResponse])
async def get_question(
    question_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Question).where(Question.id == question_id)
    result = await db.execute(query)
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found",
        )
    if current_user.role == UserRole.CANDIDATE:
        return QuestionCandidateResponse(
            id=question.id,
            type=question.type,
            title=question.title,
            content_rich_text=question.content_rich_text,
            options=question.options,
            points=question.points,
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

@router.post("/{question_id}/submit", response_model=CodeSubmitResponse)
async def submit_question_code(
    question_id: uuid.UUID,
    req: CodeSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.sandbox_service import sandbox_service
    
    # Fetch question and get correct_answer
    result = await db.execute(select(Question).where(Question.id == question_id))
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
        
    correct_answer = question.correct_answer or {}
    test_cases = []
    if isinstance(correct_answer, dict):
        test_cases = correct_answer.get("test_cases", [])
    elif isinstance(correct_answer, list):
        test_cases = correct_answer

    # If no test cases configured, provide a default echo test case
    if not test_cases:
        test_cases = [{"input": "", "output": ""}]

    lang = req.language.lower()
    if lang == "c++":
        lang = "cpp"

    test_results = []
    overall_passed = True

    for i, tc in enumerate(test_cases):
        input_data = str(tc.get("input", ""))
        expected = str(tc.get("output", "")).strip()

        try:
            exec_res = await sandbox_service.execute_async(
                language=lang,
                source_code=req.code,
                stdin=input_data,
                timeout_sec=5.0,
                memory_mb=128
            )
            actual = exec_res.stdout.strip()
            passed = (exec_res.status == "success" and (actual == expected or not expected))
            if not passed:
                overall_passed = False

            test_results.append(TestResult(
                input=input_data,
                expected=expected,
                actual=actual,
                passed=passed,
                status=exec_res.status,
                wall_time_ms=float(exec_res.wall_time_ms),
                error=exec_res.stderr
            ))
        except Exception as e:
            overall_passed = False
            test_results.append(TestResult(
                input=input_data,
                expected=expected,
                actual="",
                passed=False,
                status="error",
                wall_time_ms=0.0,
                error=str(e)
            ))

    return CodeSubmitResponse(
        status="success",
        overall_passed=overall_passed,
        test_results=test_results
    )


_CSV_TYPE_ALIASES = {
    "mcq": QuestionType.MCQ_SINGLE, "mcq_single": QuestionType.MCQ_SINGLE, "single": QuestionType.MCQ_SINGLE,
    "multiple_choice": QuestionType.MCQ_SINGLE, "multiple-choice": QuestionType.MCQ_SINGLE,
    "mcq_multi": QuestionType.MCQ_MULTI, "multi": QuestionType.MCQ_MULTI, "multiple_select": QuestionType.MCQ_MULTI,
    "short": QuestionType.SHORT_ANSWER, "short_answer": QuestionType.SHORT_ANSWER,
    "essay": QuestionType.ESSAY, "coding": QuestionType.CODING, "code": QuestionType.CODING, "sql": QuestionType.SQL,
}
_MAX_CSV_BYTES = 2 * 1024 * 1024
_MAX_CSV_ROWS = 2000


def _csv_question_type(raw: str, has_options: bool) -> QuestionType:
    key = (raw or "").strip().lower()
    if not key:
        return QuestionType.MCQ_SINGLE if has_options else QuestionType.SHORT_ANSWER
    if key in _CSV_TYPE_ALIASES:
        return _CSV_TYPE_ALIASES[key]
    return QuestionType(key.upper())  # raises ValueError for unknown types


@router.post("/bulk", response_model=dict)
async def bulk_upload_questions(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
):
    """Import questions from CSV.

    Columns: title, content, type, difficulty, points, options, correct_answer[, rubric].
    ``options`` and multi-select answers are ``|``-separated. Rows that fail
    validation are skipped and reported with their line number.
    """
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")
    contents = await file.read()
    if len(contents) > _MAX_CSV_BYTES:
        raise HTTPException(status_code=413, detail="CSV is larger than 2 MB.")
    try:
        text = contents.decode("utf-8-sig")  # tolerate Excel's BOM
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded.")

    reader = csv.DictReader(io.StringIO(text))
    questions_to_insert, errors = [], []
    for line_no, row in enumerate(reader, start=2):  # line 1 is the header
        if len(questions_to_insert) + len(errors) >= _MAX_CSV_ROWS:
            errors.append({"line": line_no, "error": f"Row limit of {_MAX_CSV_ROWS} reached; remaining rows ignored."})
            break
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        try:
            title = row.get("title", "")
            content = row.get("content", "") or title
            if not title:
                raise ValueError("title is required")
            options = [o.strip() for o in row.get("options", "").split("|") if o.strip()]
            qtype = _csv_question_type(row.get("type", ""), bool(options))
            answer: object = row.get("correct_answer", "")
            if qtype in (QuestionType.MCQ_SINGLE, QuestionType.MCQ_MULTI):
                if len(options) < 2:
                    raise ValueError("multiple-choice questions need at least two '|'-separated options")
                if qtype == QuestionType.MCQ_MULTI:
                    answer = [a.strip() for a in str(answer).split("|") if a.strip()]
                    missing = [a for a in answer if a not in options]
                else:
                    missing = [] if answer in options else [answer]
                if not answer or missing:
                    raise ValueError(f"correct_answer must be one of the options (got {missing or 'nothing'})")
            points = float(row.get("points") or 1)
            if points <= 0:
                raise ValueError("points must be positive")
            questions_to_insert.append(Question(
                id=uuid.uuid4(),
                institution_id=current_user.institution_id,
                title=title[:255],
                content_rich_text=content,
                type=qtype,
                difficulty=(row.get("difficulty") or "medium").upper(),
                points=points,
                options=[{"id": o, "text": o} for o in options] if options else None,
                correct_answer=answer or None,
                rubric=row.get("rubric") or None,
            ))
        except ValueError as exc:
            errors.append({"line": line_no, "error": str(exc)})

    if not questions_to_insert:
        summary = "; ".join(f"line {e['line']}: {e['error']}" for e in errors[:3])
        raise HTTPException(status_code=400, detail=f"No valid questions found in CSV. {summary}".strip())
    db.add_all(questions_to_insert)
    await db.commit()
    return {"status": "success", "inserted": len(questions_to_insert), "skipped": len(errors), "errors": errors[:50]}
