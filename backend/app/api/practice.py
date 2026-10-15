"""LeetCode-style practice: problem bank, run/submit judge, progress and admin authoring."""

from collections import defaultdict
import json
import os
from datetime import date, datetime, timedelta, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import RateLimiter, get_current_user, log_audit_event, require_roles
from app.core.database import get_db
from app.core.logging import logger
from app.core.practice_topics import EXTRA_TOPICS, TOPICS
from app.core.user_slots import UserSlot
from app.models.contest import Contest, ContestProblem
from app.models.practice import (
    JudgeMode,
    PracticeProblem,
    PracticeSubmission,
    PracticeTestCase,
    ProblemDifficulty,
    Verdict,
)
from app.models.exam import Exam
from app.models.question import ExamQuestion, Question, QuestionType
from app.models.session import ExamSession, SessionStatus
from app.models.user import User, UserRole
from app.schemas.practice import (
    Language,
    CaseResultOut,
    DifficultyProgress,
    ExampleCase,
    LeaderboardEntry,
    PracticeStats,
    ProblemAdminListItem,
    ProblemAdminOut,
    ProblemDetail,
    ProblemList,
    ProblemListItem,
    ProblemUpsert,
    RunRequest,
    SubmissionHistory,
    SubmissionHistoryItem,
    TopicProgress,
    RunResponse,
    SubmissionOut,
    SubmitRequest,
    SubmitResponse,
    ValidationReport,
)
from app.services.judge_queue import judge_queue
from app.services.practice_judge import (
    MAX_STDIO_INPUT_BYTES,
    SUPPORTED_LANGUAGES,
    JudgeCase,
    JudgeOutcome,
    JudgeSpecError,
    describe_function_io,
    judge,
    normalize_function_input,
    normalize_function_output,
    starter_code_map,
    validate_function_spec,
)

router = APIRouter(prefix="/practice", tags=["Practice"])
_AUTHOR_ROLES = [UserRole.ADMIN]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def contest_locked_problem_ids(db: AsyncSession) -> set[uuid.UUID]:
    """Problems of published contests that have not ended: hidden from practice until the end."""
    rows = await db.execute(
        select(ContestProblem.problem_id)
        .join(Contest, Contest.id == ContestProblem.contest_id)
        .where(Contest.is_published.is_(True), Contest.ends_at > datetime.now(timezone.utc))
    )
    return set(rows.scalars().all())


async def _get_problem(db: AsyncSession, slug: str, *, published_only: bool) -> PracticeProblem:
    query = select(PracticeProblem).options(selectinload(PracticeProblem.test_cases)).where(PracticeProblem.slug == slug)
    if published_only:
        query = query.where(PracticeProblem.is_published.is_(True))
    problem = (await db.execute(query)).scalar_one_or_none()
    if problem is None or (published_only and problem.id in await contest_locked_problem_ids(db)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Problem not found")
    return problem


# Queued submissions and engine outages are not the student's attempts.
_NOT_ATTEMPTS = (Verdict.PENDING, Verdict.SYSTEM_ERROR)


async def _user_status_map(db: AsyncSession, user_id: uuid.UUID) -> dict[uuid.UUID, str]:
    rows = await db.execute(
        select(
            PracticeSubmission.problem_id,
            func.max(case((PracticeSubmission.verdict == Verdict.ACCEPTED, 1), else_=0)),
        )
        .where(PracticeSubmission.user_id == user_id, PracticeSubmission.verdict.not_in(_NOT_ATTEMPTS))
        .group_by(PracticeSubmission.problem_id)
    )
    return {pid: ("solved" if solved else "attempted") for pid, solved in rows.all()}


async def _acceptance_map(db: AsyncSession) -> dict[uuid.UUID, tuple[int, int]]:
    rows = await db.execute(
        select(
            PracticeSubmission.problem_id,
            func.count(PracticeSubmission.id),
            func.sum(case((PracticeSubmission.verdict == Verdict.ACCEPTED, 1), else_=0)),
        )
        .where(PracticeSubmission.verdict.not_in(_NOT_ATTEMPTS))
        .group_by(PracticeSubmission.problem_id)
    )
    return {pid: (int(total), int(accepted or 0)) for pid, total, accepted in rows.all()}


def _rate(total_accepted: Optional[tuple[int, int]]) -> Optional[float]:
    if not total_accepted or total_accepted[0] == 0:
        return None
    total, accepted = total_accepted
    return round(100.0 * accepted / total, 1)


CALIBRATION_MIN_SUBMISSIONS = 20


def _suggested_difficulty(current: ProblemDifficulty, total_accepted: Optional[tuple[int, int]]) -> Optional[ProblemDifficulty]:
    """Difficulty implied by acceptance: >= 60% Easy, >= 35% Medium, otherwise Hard."""
    if not total_accepted or total_accepted[0] < CALIBRATION_MIN_SUBMISSIONS:
        return None
    rate = 100.0 * total_accepted[1] / total_accepted[0]
    implied = ProblemDifficulty.EASY if rate >= 60 else ProblemDifficulty.MEDIUM if rate >= 35 else ProblemDifficulty.HARD
    return implied if implied != current else None


def _languages(problem: PracticeProblem) -> list[str]:
    if problem.judge_mode == JudgeMode.SQL:
        return ["sql"]
    if problem.judge_mode == JudgeMode.FUNCTION:
        return list(SUPPORTED_LANGUAGES)
    return ["python", "javascript", "java", "cpp", "c"]


def _case_out(outcome: JudgeOutcome, cases: list[JudgeCase], *, reveal_hidden: bool, custom_index: Optional[int] = None) -> list[CaseResultOut]:
    out = []
    for r in outcome.cases:
        jc = cases[r.index]
        visible = jc.is_sample or reveal_hidden
        out.append(
            CaseResultOut(
                index=r.index,
                passed=r.passed,
                input=jc.input if visible else None,
                expected=jc.expected if visible else None,
                output=r.output if visible else None,
                stdout=r.stdout if visible else "",
                runtime_ms=round(r.runtime_ms, 2) if r.runtime_ms is not None else None,
                error=(r.error if visible else (r.error or "").splitlines()[0][:300] if r.error else None),
                is_custom=r.index == custom_index,
            )
        )
    return out


def _judge_cases(problem: PracticeProblem, *, samples_only: bool) -> list[JudgeCase]:
    return [
        JudgeCase(tc.input_data, tc.expected_output, tc.is_sample)
        for tc in problem.test_cases
        if tc.is_sample or not samples_only
    ]


def _raise_spec_error(exc: JudgeSpecError):
    raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc


# ---------------------------------------------------------------------------
# Student endpoints
# ---------------------------------------------------------------------------

_DIFFICULTY_RANK = {ProblemDifficulty.EASY: 0, ProblemDifficulty.MEDIUM: 1, ProblemDifficulty.HARD: 2}


def _number_key(p: PracticeProblem) -> tuple:
    return (p.number is None, p.number or 0, p.title)


@router.get("/problems", response_model=ProblemList)
async def list_problems(
    difficulty: Optional[ProblemDifficulty] = None,
    tag: Optional[str] = None,
    topic: Optional[str] = Query(default=None, max_length=64),
    search: Optional[str] = Query(default=None, max_length=100),
    status_filter: Optional[str] = Query(default=None, alias="status", pattern="^(solved|attempted|todo)$"),
    sort: str = Query(default="number", pattern="^(number|difficulty|title|acceptance)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(PracticeProblem).where(PracticeProblem.is_published.is_(True))
    if difficulty:
        query = query.where(PracticeProblem.difficulty == difficulty)
    if topic:
        query = query.where(PracticeProblem.topic == topic)
    locked = await contest_locked_problem_ids(db)
    problems = [p for p in (await db.execute(query)).scalars().all() if p.id not in locked]
    if search:
        needle = search.strip().lower().lstrip("#")
        problems = [
            p for p in problems
            if needle in p.title.lower() or needle in p.slug or (p.number is not None and needle == str(p.number))
            or any(needle == t.lower() for t in p.tags or [])
        ]

    statuses = await _user_status_map(db, current_user.id)
    acceptance = await _acceptance_map(db)
    if sort == "difficulty":
        problems.sort(key=lambda p: (_DIFFICULTY_RANK[p.difficulty], *_number_key(p)))
    elif sort == "title":
        problems.sort(key=lambda p: p.title.lower())
    elif sort == "acceptance":
        problems.sort(key=lambda p: (-(_rate(acceptance.get(p.id)) or -1), *_number_key(p)))
    else:
        problems.sort(key=_number_key)
    items = []
    for p in problems:
        if tag and tag.lower() not in [t.lower() for t in p.tags or []]:
            continue
        st = statuses.get(p.id, "todo")
        if status_filter and st != status_filter:
            continue
        items.append(ProblemListItem(
            id=p.id, number=p.number, topic=p.topic, slug=p.slug, title=p.title, difficulty=p.difficulty, tags=p.tags or [],
            acceptance_rate=_rate(acceptance.get(p.id)), status=st,
        ))
    return ProblemList(items=items, total=len(items))


@router.get("/tags", response_model=list[str])
async def list_tags(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (await db.execute(select(PracticeProblem.tags).where(PracticeProblem.is_published.is_(True)))).scalars().all()
    return sorted({t for tags in rows for t in (tags or [])})


@router.get("/topics", response_model=list[TopicProgress])
async def list_topics(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Topics in syllabus order with the current user's progress in each."""
    return await _topic_progress(db, current_user.id)


async def _topic_progress(db: AsyncSession, user_id: uuid.UUID) -> list[TopicProgress]:

    problems = (await db.execute(
        select(PracticeProblem.id, PracticeProblem.topic).where(PracticeProblem.is_published.is_(True))
    )).all()
    statuses = await _user_status_map(db, user_id)
    counts: dict[str, list[int]] = {}
    for pid, topic in problems:
        row = counts.setdefault(topic or "Other", [0, 0, 0])
        row[2] += 1
        st = statuses.get(pid)
        if st == "solved":
            row[0] += 1
        elif st == "attempted":
            row[1] += 1
    order = {t: i for i, t in enumerate(TOPICS + EXTRA_TOPICS)}
    return [
        TopicProgress(topic=t, solved=v[0], attempted=v[1], total=v[2])
        for t, v in sorted(counts.items(), key=lambda kv: (order.get(kv[0], len(order)), kv[0]))
    ]


@router.get("/problems/{slug}", response_model=ProblemDetail)
async def get_problem(slug: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    problem = await _get_problem(db, slug, published_only=current_user.role != UserRole.ADMIN)
    statuses = await _user_status_map(db, current_user.id)
    status_value = statuses.get(problem.id, "todo")
    # Editorials are a reward for solving: hidden until the user has an accepted submission.
    show_editorial = status_value == "solved" or current_user.role == UserRole.ADMIN
    return problem_detail(problem, status_value, show_editorial=show_editorial)


def problem_detail(problem: PracticeProblem, status_value: str, *, show_editorial: bool) -> ProblemDetail:
    input_format, output_format = problem.input_format, problem.output_format
    if problem.judge_mode == JudgeMode.FUNCTION and problem.function_spec and not (input_format and output_format):
        default_in, default_out = describe_function_io(problem.function_spec, problem.compare_mode)
        input_format, output_format = input_format or default_in, output_format or default_out
    return ProblemDetail(
        id=problem.id,
        number=problem.number,
        topic=problem.topic,
        slug=problem.slug,
        title=problem.title,
        difficulty=problem.difficulty,
        tags=problem.tags or [],
        statement=problem.statement,
        input_format=input_format,
        output_format=output_format,
        constraints=problem.constraints,
        complexity=problem.complexity,
        editorial=problem.editorial if show_editorial else None,
        has_editorial=bool(problem.editorial),
        hints=problem.hints or [],
        judge_mode=problem.judge_mode,
        function_spec=problem.function_spec,
        sql_schema=problem.sql_schema,
        compare_mode=problem.compare_mode,
        examples=[
            ExampleCase(input=tc.input_data, expected_output=tc.expected_output, explanation=tc.explanation)
            for tc in problem.test_cases if tc.is_sample
        ],
        starter_code=starter_code_map(problem),
        languages=_languages(problem),
        time_limit_ms=problem.time_limit_ms,
        memory_limit_mb=problem.memory_limit_mb,
        status=status_value,
        has_reference_solution=bool(problem.reference_solution),
    )


@router.post("/problems/{slug}/run", response_model=RunResponse, dependencies=[Depends(RateLimiter(30, 60, local_fallback=True, per_user=True))])
async def run_code(
    slug: str,
    payload: RunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run against the sample cases (plus optional custom input). Nothing is stored."""
    problem = await _get_problem(db, slug, published_only=current_user.role != UserRole.ADMIN)
    return await run_samples(problem, payload, current_user)


async def run_samples(problem: PracticeProblem, payload: RunRequest, current_user: User) -> RunResponse:
    if payload.language not in _languages(problem):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{payload.language} is not available for this problem")
    cases = _judge_cases(problem, samples_only=True)
    custom_index = None
    if payload.custom_input and payload.custom_input.strip():
        try:
            custom = (
                normalize_function_input(payload.custom_input, problem.function_spec)
                if problem.judge_mode == JudgeMode.FUNCTION
                else payload.custom_input
            )
        except JudgeSpecError as exc:
            _raise_spec_error(exc)
        expected = None
        ref = problem.reference_solution
        if ref and ref.get("code"):
            # Compute the expected answer for the custom input from the reference solution.
            ref_outcome = await judge(problem, ref.get("language", "python"), ref["code"], [JudgeCase(custom, None)])
            if ref_outcome.cases and ref_outcome.cases[0].error is None:
                expected = ref_outcome.cases[0].output
        custom_index = len(cases)
        cases.append(JudgeCase(custom, expected, is_sample=True))

    async with UserSlot("practice", current_user.id):
        try:
            outcome = await judge(problem, payload.language, payload.code, cases)
        except JudgeSpecError as exc:
            _raise_spec_error(exc)
    return RunResponse(
        verdict=outcome.verdict,
        cases=_case_out(outcome, cases, reveal_hidden=False, custom_index=custom_index),
        passed_count=outcome.passed_count,
        total_count=outcome.total_count,
        runtime_ms=outcome.runtime_ms,
        compile_output=outcome.compile_output,
        error=outcome.error,
    )


SUBMIT_WAIT_SECONDS = float(os.getenv("SUBMIT_WAIT_SECONDS", "20"))


def _submission_response(problem_id: uuid.UUID, submission: PracticeSubmission) -> SubmitResponse:
    compile_output = None
    if submission.verdict == Verdict.COMPILE_ERROR and submission.failure:
        compile_output = submission.failure.get("error")
    return SubmitResponse(
        id=submission.id,
        problem_id=problem_id,
        language=submission.language,
        verdict=submission.verdict,
        passed_count=submission.passed_count,
        total_count=submission.total_count,
        runtime_ms=submission.runtime_ms,
        failure=submission.failure,
        created_at=submission.created_at,
        compile_output=compile_output,
    )


async def _judge_submission(db: AsyncSession, submission: PracticeSubmission) -> Verdict:
    """Queue handler: judge one submission against every test (stopping at the first failure)."""
    problem = (await db.execute(
        select(PracticeProblem).options(selectinload(PracticeProblem.test_cases)).where(PracticeProblem.id == submission.problem_id)
    )).scalar_one()
    cases = _judge_cases(problem, samples_only=False)
    # Give the connection back while the engine runs (seconds per job, JUDGE_WORKERS jobs per
    # process); the session reconnects to store the verdict. expire_on_commit=False keeps the
    # loaded problem and submission usable.
    await db.commit()
    outcome = await judge(problem, submission.language, submission.source_code, cases, stop_on_failure=True)

    failure = None
    if outcome.failed_index is not None:
        failed = _case_out(outcome, cases, reveal_hidden=False)
        detail = next((c for c in failed if c.index == outcome.failed_index), None)
        failure = {
            "case_number": outcome.failed_index + 1,
            "is_sample": cases[outcome.failed_index].is_sample,
            **(detail.model_dump(exclude={"index", "is_custom"}) if detail else {}),
        }
    elif outcome.verdict in (Verdict.COMPILE_ERROR, Verdict.SYSTEM_ERROR):
        failure = {"error": (outcome.compile_output or outcome.error or "")[:4000]}
    if outcome.verdict == Verdict.SYSTEM_ERROR:
        logger.error("practice.submit_system_error", problem=problem.slug, error=outcome.error)
        failure = {"error": "The code execution engine is unavailable. Please try again shortly."}

    submission.verdict = outcome.verdict
    submission.passed_count = outcome.passed_count
    submission.total_count = outcome.total_count
    submission.runtime_ms = outcome.runtime_ms if outcome.verdict == Verdict.ACCEPTED else None
    submission.failure = failure
    return outcome.verdict


judge_queue.handler = _judge_submission


@router.post(
    "/problems/{slug}/submit",
    response_model=SubmitResponse,
    dependencies=[Depends(RateLimiter(10, 60, local_fallback=True, per_user=True))],
    responses={202: {"model": SubmitResponse, "description": "Queued: poll GET /api/practice/submissions/{id}"}},
)
async def submit_code(
    slug: str,
    payload: SubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Queue the submission for judging against every test case and wait briefly for the verdict.

    Usually the verdict is ready within the wait (200). Under heavy load the response is
    202 with ``verdict: PENDING``; poll ``GET /api/practice/submissions/{id}`` for the result.
    """
    problem = await _get_problem(db, slug, published_only=current_user.role != UserRole.ADMIN)
    return await enqueue_submission(db, problem, payload, current_user)


async def enqueue_submission(
    db: AsyncSession,
    problem: PracticeProblem,
    payload: SubmitRequest,
    current_user: User,
    contest_id: Optional[uuid.UUID] = None,
):
    """Store a PENDING submission, wake the judge workers and wait up to SUBMIT_WAIT_SECONDS.

    Returns the verdict (200) or, if judging takes longer, a 202 with ``verdict: PENDING``.
    """
    if payload.language not in _languages(problem):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{payload.language} is not available for this problem")
    if not problem.test_cases:
        raise HTTPException(status.HTTP_409_CONFLICT, "This problem has no test cases yet")
    pending = (await db.execute(
        select(func.count(PracticeSubmission.id)).where(
            PracticeSubmission.user_id == current_user.id, PracticeSubmission.verdict == Verdict.PENDING,
        )
    )).scalar_one()
    if pending:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Your previous submission is still being judged. Please wait for it.")

    submission = PracticeSubmission(
        problem_id=problem.id,
        user_id=current_user.id,
        language=payload.language,
        source_code=payload.code,
        verdict=Verdict.PENDING,
        passed_count=0,
        total_count=len(problem.test_cases),
        contest_id=contest_id,
    )
    db.add(submission)
    await db.commit()
    submission_id, problem_id = submission.id, problem.id
    # Give the connection back to the pool while waiting: hundreds of students may be waiting
    # at once, and a held connection each would exhaust the pool.
    await db.close()

    judge_queue.ensure_started()
    judge_queue.track(submission_id)
    judge_queue.notify()
    await judge_queue.wait_for(submission_id, timeout=SUBMIT_WAIT_SECONDS)

    submission = await db.get(PracticeSubmission, submission_id, populate_existing=True)
    body = _submission_response(problem_id, submission)
    if submission.verdict == Verdict.PENDING:
        return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=body.model_dump(mode="json"))
    return body


@router.get("/submissions/{submission_id}", response_model=SubmitResponse)
async def get_my_submission(
    submission_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user),
):
    """One of your submissions - poll this while ``verdict`` is ``PENDING``."""
    submission = await db.get(PracticeSubmission, submission_id)
    if submission is None or submission.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Submission not found")
    return _submission_response(submission.problem_id, submission)


@router.get("/problems/{slug}/submissions", response_model=list[SubmissionOut])
async def my_submissions(slug: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    problem = await _get_problem(db, slug, published_only=current_user.role != UserRole.ADMIN)
    rows = (
        await db.execute(
            select(PracticeSubmission)
            .where(
                PracticeSubmission.problem_id == problem.id,
                PracticeSubmission.user_id == current_user.id,
                PracticeSubmission.verdict != Verdict.SYSTEM_ERROR,
            )
            .order_by(PracticeSubmission.created_at.desc())
            .limit(50)
        )
    ).scalars().all()
    return [SubmissionOut.model_validate(r) for r in rows]


@router.get("/submissions", response_model=SubmissionHistory)
async def my_submission_history(
    verdict: Optional[Verdict] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """All of the current user's practice submissions, newest first (source code omitted)."""
    conditions = [PracticeSubmission.user_id == current_user.id, PracticeSubmission.verdict != Verdict.SYSTEM_ERROR]
    if verdict:
        conditions.append(PracticeSubmission.verdict == verdict)
    total = (await db.execute(select(func.count(PracticeSubmission.id)).where(*conditions))).scalar_one()
    rows = (await db.execute(
        select(PracticeSubmission, PracticeProblem.number, PracticeProblem.slug, PracticeProblem.title)
        .join(PracticeProblem, PracticeProblem.id == PracticeSubmission.problem_id)
        .where(*conditions)
        .order_by(PracticeSubmission.created_at.desc())
        .limit(limit).offset(offset)
    )).all()
    return SubmissionHistory(total=total, items=[
        SubmissionHistoryItem(
            id=sub.id, problem_number=number, problem_slug=slug, problem_title=title, language=sub.language,
            verdict=sub.verdict, passed_count=sub.passed_count, total_count=sub.total_count,
            runtime_ms=sub.runtime_ms, created_at=sub.created_at,
        )
        for sub, number, slug, title in rows
    ])


@router.get("/stats/me", response_model=PracticeStats)
async def my_stats(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    totals = dict(
        (await db.execute(
            select(PracticeProblem.difficulty, func.count(PracticeProblem.id))
            .where(PracticeProblem.is_published.is_(True))
            .group_by(PracticeProblem.difficulty)
        )).all()
    )
    solved_rows = (await db.execute(
        select(PracticeProblem.difficulty, func.count(func.distinct(PracticeSubmission.problem_id)))
        .join(PracticeProblem, PracticeProblem.id == PracticeSubmission.problem_id)
        .where(PracticeSubmission.user_id == current_user.id, PracticeSubmission.verdict == Verdict.ACCEPTED)
        .group_by(PracticeProblem.difficulty)
    )).all()
    solved = dict(solved_rows)

    since = datetime.now(timezone.utc) - timedelta(days=365)
    subs = (await db.execute(
        select(PracticeSubmission.created_at, PracticeSubmission.verdict, PracticeProblem.title, PracticeProblem.slug, PracticeSubmission.language)
        .join(PracticeProblem, PracticeProblem.id == PracticeSubmission.problem_id)
        .where(
            PracticeSubmission.user_id == current_user.id,
            PracticeSubmission.created_at >= since,
            PracticeSubmission.verdict.not_in(_NOT_ATTEMPTS),
        )
        .order_by(PracticeSubmission.created_at.desc())
    )).all()
    activity: dict[str, int] = defaultdict(int)
    for created, *_ in subs:
        activity[created.date().isoformat()] += 1
    streak, day = 0, date.today()
    if day.isoformat() not in activity:
        day -= timedelta(days=1)  # today's streak isn't broken until the day ends
    while day.isoformat() in activity:
        streak += 1
        day -= timedelta(days=1)

    total_subs = len(subs)
    accepted = sum(1 for s in subs if s[1] == Verdict.ACCEPTED)
    return PracticeStats(
        solved_total=sum(solved.values()),
        problems_total=sum(totals.values()),
        by_difficulty={
            d.value: DifficultyProgress(solved=solved.get(d, 0), total=totals.get(d, 0)) for d in ProblemDifficulty
        },
        submissions_total=total_subs,
        accepted_total=accepted,
        acceptance_rate=round(100 * accepted / total_subs, 1) if total_subs else None,
        current_streak_days=streak,
        activity=dict(activity),
        recent=[
            {"title": t, "slug": sl, "verdict": v.value, "language": lang, "created_at": c.isoformat()}
            for c, v, t, sl, lang in subs[:10]
        ],
        by_topic=await _topic_progress(db, current_user.id),
    )


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def leaderboard(limit: int = Query(default=20, ge=1, le=100), db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (await db.execute(
        select(PracticeSubmission.user_id, User.full_name, PracticeProblem.difficulty, func.count(func.distinct(PracticeSubmission.problem_id)))
        .join(PracticeProblem, PracticeProblem.id == PracticeSubmission.problem_id)
        .join(User, User.id == PracticeSubmission.user_id)
        .where(PracticeSubmission.verdict == Verdict.ACCEPTED)
        .group_by(PracticeSubmission.user_id, User.full_name, PracticeProblem.difficulty)
    )).all()
    per_user: dict[uuid.UUID, dict] = {}
    for user_id, name, difficulty, n in rows:
        entry = per_user.setdefault(user_id, {"name": name, "EASY": 0, "MEDIUM": 0, "HARD": 0})
        entry[difficulty.value] = n
    # Weighted by difficulty, then by raw count.
    ranked = sorted(per_user.items(), key=lambda kv: (-(kv[1]["EASY"] + 2 * kv[1]["MEDIUM"] + 3 * kv[1]["HARD"]), kv[1]["name"]))
    return [
        LeaderboardEntry(rank=i + 1, user_id=uid, name=d["name"], solved=d["EASY"] + d["MEDIUM"] + d["HARD"],
                         easy=d["EASY"], medium=d["MEDIUM"], hard=d["HARD"])
        for i, (uid, d) in enumerate(ranked[:limit])
    ]


# ---------------------------------------------------------------------------
# Admin authoring
# ---------------------------------------------------------------------------

def _apply_upsert(problem: PracticeProblem, payload: ProblemUpsert) -> None:
    spec = payload.function_spec.model_dump() if payload.function_spec else None
    test_cases = []
    try:
        if payload.judge_mode == JudgeMode.FUNCTION:
            validate_function_spec(spec)
        for i, tc in enumerate(payload.test_cases):
            if payload.judge_mode == JudgeMode.FUNCTION:
                inp = normalize_function_input(tc.input_data, spec)
                exp = normalize_function_output(tc.expected_output)
            elif payload.judge_mode == JudgeMode.SQL:
                exp = normalize_function_output(tc.expected_output)
                if not isinstance(json.loads(exp), list):
                    raise JudgeSpecError(f"Test case {i + 1}: expected output must be a JSON array of rows")
                inp = tc.input_data
            else:
                if len(tc.input_data.encode()) > MAX_STDIO_INPUT_BYTES:
                    raise JudgeSpecError(
                        f"Test case {i + 1}: stdin input exceeds {MAX_STDIO_INPUT_BYTES // 1024} KB "
                        "(use a FUNCTION-mode problem for larger inputs)"
                    )
                inp, exp = tc.input_data, tc.expected_output
            test_cases.append(PracticeTestCase(
                input_data=inp, expected_output=exp, is_sample=tc.is_sample, explanation=tc.explanation, order_index=i,
            ))
    except JudgeSpecError as exc:
        _raise_spec_error(exc)

    if payload.judge_mode == JudgeMode.SQL and not (payload.sql_schema or "").strip():
        _raise_spec_error(JudgeSpecError("SQL problems need a schema (CREATE TABLE statements)"))
    if payload.compare_mode == "checker" and not problem.checker:
        _raise_spec_error(JudgeSpecError(
            "compare_mode 'checker' is only available for problems whose checker ships with the question bank"
        ))
    for field in ("slug", "number", "topic", "title", "difficulty", "tags", "statement", "input_format", "output_format",
                  "constraints", "complexity", "editorial", "hints", "judge_mode", "sql_schema",
                  "compare_mode", "starter_code", "reference_solution", "time_limit_ms", "memory_limit_mb", "is_published"):
        setattr(problem, field, getattr(payload, field))
    problem.function_spec = {k: v for k, v in spec.items() if v is not None} if spec else None
    problem.test_cases = test_cases


async def _ensure_unique_number(db: AsyncSession, number: Optional[int], problem_id: Optional[uuid.UUID] = None) -> None:
    if number is None:
        return
    query = select(PracticeProblem.id).where(PracticeProblem.number == number)
    if problem_id is not None:
        query = query.where(PracticeProblem.id != problem_id)
    if (await db.execute(query)).scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, f"Problem number {number} is already in use")


@router.get("/admin/problems", response_model=list[ProblemAdminListItem])
async def admin_list_problems(db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles(_AUTHOR_ROLES))):
    problems = (await db.execute(
        select(PracticeProblem).options(selectinload(PracticeProblem.test_cases))
    )).scalars().all()
    problems = sorted(problems, key=_number_key)
    acceptance = await _acceptance_map(db)
    return [
        ProblemAdminListItem(
            id=p.id, number=p.number, topic=p.topic, slug=p.slug, title=p.title, difficulty=p.difficulty, tags=p.tags or [], is_published=p.is_published,
            test_case_count=len(p.test_cases), sample_count=sum(1 for t in p.test_cases if t.is_sample),
            submissions=acceptance.get(p.id, (0, 0))[0], acceptance_rate=_rate(acceptance.get(p.id)),
            suggested_difficulty=_suggested_difficulty(p.difficulty, acceptance.get(p.id)), updated_at=p.updated_at,
        )
        for p in problems
    ]


@router.get("/admin/problems/{problem_id}", response_model=ProblemAdminOut)
async def admin_get_problem(problem_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles(_AUTHOR_ROLES))):
    problem = (await db.execute(
        select(PracticeProblem).options(selectinload(PracticeProblem.test_cases)).where(PracticeProblem.id == problem_id)
    )).scalar_one_or_none()
    if problem is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Problem not found")
    return ProblemAdminOut.model_validate(problem)


@router.post("/admin/problems", response_model=ProblemAdminOut, status_code=status.HTTP_201_CREATED)
async def admin_create_problem(payload: ProblemUpsert, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles(_AUTHOR_ROLES))):
    if (await db.execute(select(PracticeProblem.id).where(PracticeProblem.slug == payload.slug))).scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, f"A problem with slug '{payload.slug}' already exists")
    await _ensure_unique_number(db, payload.number)
    problem = PracticeProblem(created_by=current_user.id)
    _apply_upsert(problem, payload)
    db.add(problem)
    await log_audit_event(db=db, action="PRACTICE_PROBLEM_CREATED", resource_type="practice_problem", resource_id=payload.slug,
                          details={"title": payload.title}, user_id=current_user.id, institution_id=current_user.institution_id)
    await db.commit()
    return await admin_get_problem(problem.id, db, current_user)


@router.put("/admin/problems/{problem_id}", response_model=ProblemAdminOut)
async def admin_update_problem(problem_id: uuid.UUID, payload: ProblemUpsert, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles(_AUTHOR_ROLES))):
    problem = (await db.execute(
        select(PracticeProblem).options(selectinload(PracticeProblem.test_cases)).where(PracticeProblem.id == problem_id)
    )).scalar_one_or_none()
    if problem is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Problem not found")
    clash = (await db.execute(
        select(PracticeProblem.id).where(PracticeProblem.slug == payload.slug, PracticeProblem.id != problem_id)
    )).scalar_one_or_none()
    if clash:
        raise HTTPException(status.HTTP_409_CONFLICT, f"A problem with slug '{payload.slug}' already exists")
    await _ensure_unique_number(db, payload.number, problem_id)
    _apply_upsert(problem, payload)
    await log_audit_event(db=db, action="PRACTICE_PROBLEM_UPDATED", resource_type="practice_problem", resource_id=str(problem_id),
                          details={"title": payload.title}, user_id=current_user.id, institution_id=current_user.institution_id)
    await db.commit()
    db.expire_all()
    return await admin_get_problem(problem_id, db, current_user)


@router.delete("/admin/problems/{problem_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_problem(problem_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles(_AUTHOR_ROLES))):
    problem = await db.get(PracticeProblem, problem_id)
    if problem is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Problem not found")
    await db.delete(problem)
    await log_audit_event(db=db, action="PRACTICE_PROBLEM_DELETED", resource_type="practice_problem", resource_id=str(problem_id),
                          details={"slug": problem.slug}, user_id=current_user.id, institution_id=current_user.institution_id)
    await db.commit()


@router.post("/admin/problems/{problem_id}/validate", response_model=ValidationReport)
async def admin_validate_problem(problem_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles(_AUTHOR_ROLES))):
    """Run the reference solution against every test case to prove the data is consistent."""
    problem = (await db.execute(
        select(PracticeProblem).options(selectinload(PracticeProblem.test_cases)).where(PracticeProblem.id == problem_id)
    )).scalar_one_or_none()
    if problem is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Problem not found")
    ref = problem.reference_solution or {}
    if not ref.get("code"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Add a reference solution before validating")
    cases = _judge_cases(problem, samples_only=False)
    if not cases:
        raise HTTPException(status.HTTP_409_CONFLICT, "Add test cases before validating")
    try:
        outcome = await judge(problem, ref.get("language", "python"), ref["code"], cases)
    except JudgeSpecError as exc:
        _raise_spec_error(exc)
    ok = outcome.verdict == Verdict.ACCEPTED
    failures = [c for c in _case_out(outcome, cases, reveal_hidden=True) if c.passed is False]
    message = (
        f"Reference solution passes all {outcome.total_count} test cases."
        if ok else
        f"Reference solution verdict {outcome.verdict.value}: {outcome.compile_output or outcome.error or f'{len(failures)} case(s) disagree with the expected output'}"
    )
    return ValidationReport(ok=ok, verdict=outcome.verdict, passed_count=outcome.passed_count,
                            total_count=outcome.total_count, message=message, failures=failures)


# ---------------------------------------------------------------------------
# Practice problems inside exams
# ---------------------------------------------------------------------------

class ToExamRequest(BaseModel):
    exam_id: Optional[uuid.UUID] = None
    points: float = Field(default=10.0, gt=0, le=1000)


class ExamRunRequest(BaseModel):
    session_id: uuid.UUID
    question_id: uuid.UUID
    language: Language
    code: str = Field(min_length=1, max_length=50_000)


def _exam_question_content(problem: PracticeProblem) -> str:
    parts = [problem.statement]
    if problem.sql_schema:
        parts.append("**Tables**\n\n```\n" + problem.sql_schema + "\n```")
    for i, tc in enumerate((t for t in problem.test_cases if t.is_sample), start=1):
        parts.append(f"**Example {i}**\n\n```\nInput:\n{tc.input_data}\n\nOutput:\n{tc.expected_output}\n```")
    if problem.constraints:
        parts.append("**Constraints**\n\n" + problem.constraints)
    return "\n\n".join(parts)


@router.post("/admin/problems/{problem_id}/to-exam", status_code=status.HTTP_201_CREATED)
async def admin_problem_to_exam(
    problem_id: uuid.UUID,
    payload: ToExamRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(_AUTHOR_ROLES)),
):
    """Create an exam question judged by this problem's tests (optionally adding it to an exam)."""
    problem = (await db.execute(
        select(PracticeProblem).options(selectinload(PracticeProblem.test_cases)).where(PracticeProblem.id == problem_id)
    )).scalar_one_or_none()
    if problem is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Problem not found")
    if not problem.test_cases:
        raise HTTPException(status.HTTP_409_CONFLICT, "Add test cases before using this problem in an exam")

    question = Question(
        institution_id=current_user.institution_id,
        type=QuestionType.SQL if problem.judge_mode == JudgeMode.SQL else QuestionType.CODING,
        title=problem.title,
        content_rich_text=_exam_question_content(problem),
        points=payload.points,
        difficulty=problem.difficulty.value,
        # Visible to candidates: languages and starter code only — never the tests.
        options={
            "practice_problem_id": str(problem.id),
            "judge_mode": problem.judge_mode.value,
            "allowed_languages": _languages(problem),
            "starter_code": starter_code_map(problem),
        },
        correct_answer={"practice_problem_id": str(problem.id)},
    )
    db.add(question)
    await db.flush()

    if payload.exam_id:
        exam = await db.get(Exam, payload.exam_id)
        if exam is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Exam not found")
        next_index = (await db.execute(
            select(func.count(ExamQuestion.id)).where(ExamQuestion.exam_id == exam.id)
        )).scalar_one()
        db.add(ExamQuestion(exam_id=exam.id, question_id=question.id, order_index=next_index))

    await log_audit_event(db=db, action="PRACTICE_PROBLEM_ADDED_TO_EXAM", resource_type="question", resource_id=str(question.id),
                          details={"problem": problem.slug, "exam_id": str(payload.exam_id) if payload.exam_id else None},
                          user_id=current_user.id, institution_id=current_user.institution_id)
    await db.commit()
    return {"question_id": str(question.id), "exam_id": str(payload.exam_id) if payload.exam_id else None, "title": question.title}


@router.post("/exam-run", response_model=RunResponse, dependencies=[Depends(RateLimiter(30, 60, local_fallback=True, per_user=True))])
async def exam_run_samples(
    payload: ExamRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """During an exam, run a linked question's code against its sample tests only."""
    session = await db.get(ExamSession, payload.session_id)
    if session is None or session.candidate_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exam session not found")
    if session.status != SessionStatus.IN_PROGRESS:
        raise HTTPException(status.HTTP_409_CONFLICT, "This exam session is no longer active")
    in_exam = (await db.execute(
        select(ExamQuestion.id).where(ExamQuestion.exam_id == session.exam_id, ExamQuestion.question_id == payload.question_id)
    )).scalar_one_or_none()
    question = await db.get(Question, payload.question_id) if in_exam else None
    problem_ref = (question.correct_answer or {}).get("practice_problem_id") if question and isinstance(question.correct_answer, dict) else None
    if not problem_ref:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question is not linked to a practice problem")
    problem = (await db.execute(
        select(PracticeProblem).options(selectinload(PracticeProblem.test_cases)).where(PracticeProblem.id == uuid.UUID(problem_ref))
    )).scalar_one_or_none()
    if problem is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Linked problem no longer exists")
    if payload.language not in _languages(problem):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{payload.language} is not available for this question")

    cases = _judge_cases(problem, samples_only=True)
    async with UserSlot("practice", current_user.id):
        try:
            outcome = await judge(problem, payload.language, payload.code, cases)
        except JudgeSpecError as exc:
            _raise_spec_error(exc)
    return RunResponse(
        verdict=outcome.verdict,
        cases=_case_out(outcome, cases, reveal_hidden=False),
        passed_count=outcome.passed_count,
        total_count=outcome.total_count,
        runtime_ms=outcome.runtime_ms,
        compile_output=outcome.compile_output,
        error=outcome.error,
    )
