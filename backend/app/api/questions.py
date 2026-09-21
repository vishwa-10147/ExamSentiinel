from datetime import datetime, timezone
from typing import List, Optional
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


@router.get("/{question_id}", response_model=QuestionAdminResponse)
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
    # Fetch question and get correct_answer
    result = await db.execute(select(Question).where(Question.id == question_id))
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
        
    correct_answer = question.correct_answer or {}
    test_cases = correct_answer.get("test_cases", [])
    
    if not test_cases:
        return CodeSubmitResponse(status="success", overall_passed=True, test_results=[])

    inputs = [tc.get("input", "") for tc in test_cases]
    expected_outputs = [tc.get("output", "") for tc in test_cases]

    # Queue to execution engine
    job_id = str(uuid.uuid4())
    queue_name = "examsentinel:sandbox:queue"
    result_key = f"examsentinel:sandbox:result:{job_id}"
    
    r = redis.from_url(str(settings.REDIS_URL))
    payload = json.dumps({
        "job_id": job_id,
        "language": req.language.lower(),
        "code": req.code,
        "test_cases": inputs
    })
    await r.rpush(queue_name, payload)
    
    # Wait for execution worker to process and write to result_key
    worker_result = None
    import asyncio
    for _ in range(150):
        res_bytes = await r.get(result_key)
        if res_bytes:
            worker_result = json.loads(res_bytes)
            break
        await asyncio.sleep(0.1)
    await r.aclose()
        
    if not worker_result:
        raise HTTPException(status_code=500, detail="Execution engine timeout")

    # Evaluate results
    test_results = []
    overall_passed = True
    
    worker_tc_results = worker_result.get("test_results", [])
    
    for i, tc in enumerate(test_cases):
        if i < len(worker_tc_results):
            wtc = worker_tc_results[i]
            actual = wtc.get("stdout", "").strip()
            expected = str(tc.get("output", "")).strip()
            passed = (wtc.get("status") == "success" and actual == expected)
            if not passed:
                overall_passed = False
                
            test_results.append(TestResult(
                input=str(tc.get("input", "")),
                expected=expected,
                actual=actual,
                passed=passed,
                status=wtc.get("status", "error"),
                wall_time_ms=wtc.get("wall_time_ms", 0.0),
                error=wtc.get("stderr", "")
            ))
        else:
            overall_passed = False
            test_results.append(TestResult(
                input=str(tc.get("input", "")),
                expected=str(tc.get("output", "")),
                actual="",
                passed=False,
                status="missing",
                wall_time_ms=0.0,
                error="Test case execution failed to return"
            ))

    # Here we would normally record the submission in the database for the Heatmap!
    
    return CodeSubmitResponse(
        status="success",
        overall_passed=overall_passed,
        test_results=test_results
    )


@router.post("/bulk", response_model=dict)
async def bulk_upload_questions(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN]))
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")
    
    contents = await file.read()
    try:
        text = contents.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded.")
        
    reader = csv.DictReader(io.StringIO(text))
    questions_to_insert = []
    
    for row in reader:
        # Expected CSV columns: title, content, type, difficulty, points, options, correct_answer
        try:
            q = Question(
                id=uuid.uuid4(),
                title=row.get('title', '').strip(),
                content=row.get('content', '').strip(),
                type=QuestionType(row.get('type', 'multiple_choice')),
                difficulty=QuestionDifficulty(row.get('difficulty', 'medium')),
                points=int(row.get('points', 10)),
                options=row.get('options', '').split('|') if row.get('options') else [],
                correct_answer=row.get('correct_answer', '').strip(),
                rubric=row.get('rubric', None)
            )
            questions_to_insert.append(q)
        except Exception as e:
            continue # skip invalid rows
            
    if not questions_to_insert:
        raise HTTPException(status_code=400, detail="No valid questions found in CSV.")
        
    db.add_all(questions_to_insert)
    await db.commit()
    
    return {"status": "success", "inserted": len(questions_to_insert)}
