"""Timed contests: registration, a contest problem set, judged submissions and a live leaderboard.

Rules (enforced here, not in the UI):
- Problems are hidden until the contest starts; afterwards anyone signed in can read them.
- Only registered users can submit, and only between ``starts_at`` and ``ends_at``.
- Editorials stay hidden until the contest ends.
- While a published contest has not ended, its problems are also hidden from practice
  (``practice.contest_locked_problem_ids``), so they cannot be solved or looked up there.

Scoring: the points of every solved problem. Ties are broken by penalty time, the sum over
solved problems of minutes from the start to the first accepted submission plus
``penalty_minutes`` for each rejected submission before it (compile errors are not counted),
then by the time of the last accepted submission.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import RateLimiter, get_current_user, log_audit_event, require_roles
from app.api.practice import _NOT_ATTEMPTS, _get_problem, enqueue_submission, problem_detail, run_samples
from app.core.database import get_db
from app.models.contest import Contest, ContestProblem, ContestRegistration
from app.models.practice import PracticeProblem, PracticeSubmission, Verdict
from app.models.user import User, UserRole
from app.schemas.contest import (
    ContestAdminOut,
    ContestAdminProblem,
    ContestDetail,
    ContestLeaderboard,
    ContestLeaderboardRow,
    ContestList,
    ContestProblemOut,
    ContestSubmissionOut,
    ContestSummary,
    ContestUpsert,
    LeaderboardCell,
)
from app.schemas.practice import ProblemDetail, RunRequest, RunResponse, SubmissionOut, SubmitRequest, SubmitResponse

router = APIRouter(prefix="/contests", tags=["Contests"])
_ADMIN = [UserRole.ADMIN]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes; everything is stored in UTC."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _phase(contest: Contest, now: Optional[datetime] = None) -> str:
    now = now or _now()
    if now < _utc(contest.starts_at):
        return "upcoming"
    return "running" if now < _utc(contest.ends_at) else "ended"


def _label(index: int) -> str:
    return chr(ord("A") + index)


def _is_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN


async def _get_contest(db: AsyncSession, slug: str, user: User) -> Contest:
    query = (
        select(Contest)
        .options(selectinload(Contest.problems).selectinload(ContestProblem.problem))
        .where(Contest.slug == slug)
    )
    if not _is_admin(user):
        query = query.where(Contest.is_published.is_(True))
    contest = (await db.execute(query)).scalar_one_or_none()
    if contest is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contest not found")
    return contest


async def _is_registered(db: AsyncSession, contest_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    return (await db.execute(
        select(ContestRegistration.id).where(ContestRegistration.contest_id == contest_id, ContestRegistration.user_id == user_id)
    )).first() is not None


async def _participant_counts(db: AsyncSession, contest_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not contest_ids:
        return {}
    rows = await db.execute(
        select(ContestRegistration.contest_id, func.count(ContestRegistration.id))
        .where(ContestRegistration.contest_id.in_(contest_ids))
        .group_by(ContestRegistration.contest_id)
    )
    return dict(rows.all())


def _summary(contest: Contest, *, participants: int, registered: bool, now: datetime) -> dict:
    starts, ends = _utc(contest.starts_at), _utc(contest.ends_at)
    return dict(
        id=contest.id, slug=contest.slug, title=contest.title, starts_at=starts, ends_at=ends,
        duration_minutes=int((ends - starts).total_seconds() // 60), phase=_phase(contest, now),
        problem_count=len(contest.problems), participants=participants, registered=registered,
        is_published=contest.is_published,
    )


def _contest_problem(contest: Contest, problem_slug: str) -> tuple[int, ContestProblem]:
    for i, cp in enumerate(contest.problems):
        if cp.problem.slug == problem_slug:
            return i, cp
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Problem not found in this contest")


def _require_started(contest: Contest, user: User) -> None:
    if not _is_admin(user) and _phase(contest) == "upcoming":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "The contest has not started yet")


@dataclass
class _Cell:
    solved: bool = False
    rejected: int = 0
    solved_at: Optional[datetime] = None


@dataclass
class _Standing:
    user_id: uuid.UUID
    name: str
    cells: dict[uuid.UUID, _Cell] = field(default_factory=dict)
    score: int = 0
    solved: int = 0
    penalty: int = 0
    last_accepted: Optional[datetime] = None


async def _standings(db: AsyncSession, contest: Contest) -> list[_Standing]:
    """Score every registered user from their in-window contest submissions."""
    starts, ends = _utc(contest.starts_at), _utc(contest.ends_at)
    users = (await db.execute(
        select(User.id, func.coalesce(User.display_name, User.full_name))
        .join(ContestRegistration, ContestRegistration.user_id == User.id)
        .where(ContestRegistration.contest_id == contest.id)
    )).all()
    standings = {uid: _Standing(uid, name) for uid, name in users}
    submissions = (await db.execute(
        select(PracticeSubmission.user_id, PracticeSubmission.problem_id, PracticeSubmission.verdict, PracticeSubmission.created_at)
        .where(
            PracticeSubmission.contest_id == contest.id,
            PracticeSubmission.verdict.not_in(_NOT_ATTEMPTS),
            PracticeSubmission.created_at >= starts,
            PracticeSubmission.created_at < ends,
        )
        .order_by(PracticeSubmission.created_at)
    )).all()
    points = {cp.problem_id: cp.points for cp in contest.problems}
    for user_id, problem_id, verdict, created_at in submissions:
        standing = standings.get(user_id)
        if standing is None or problem_id not in points:
            continue
        cell = standing.cells.setdefault(problem_id, _Cell())
        if cell.solved:
            continue
        if verdict == Verdict.ACCEPTED:
            cell.solved, cell.solved_at = True, _utc(created_at)
        elif verdict != Verdict.COMPILE_ERROR:
            cell.rejected += 1
    for standing in standings.values():
        for problem_id, cell in standing.cells.items():
            if not cell.solved:
                continue
            standing.score += points[problem_id]
            standing.solved += 1
            standing.penalty += int((cell.solved_at - starts).total_seconds() // 60) + cell.rejected * contest.penalty_minutes
            if standing.last_accepted is None or cell.solved_at > standing.last_accepted:
                standing.last_accepted = cell.solved_at
    far = ends + timedelta(days=1)
    return sorted(
        standings.values(),
        key=lambda s: (-s.score, s.penalty, s.last_accepted or far, s.name.lower()),
    )


async def _my_problem_status(db: AsyncSession, contest: Contest, user_id: uuid.UUID) -> dict[uuid.UUID, str]:
    rows = await db.execute(
        select(PracticeSubmission.problem_id, PracticeSubmission.verdict)
        .where(
            PracticeSubmission.contest_id == contest.id,
            PracticeSubmission.user_id == user_id,
            PracticeSubmission.verdict.not_in(_NOT_ATTEMPTS),
        )
    )
    out: dict[uuid.UUID, str] = {}
    for problem_id, verdict in rows.all():
        if verdict == Verdict.ACCEPTED:
            out[problem_id] = "solved"
        else:
            out.setdefault(problem_id, "attempted")
    return out


# ---------------------------------------------------------------------------
# Participant endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=ContestList)
async def list_contests(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = select(Contest).options(selectinload(Contest.problems)).order_by(Contest.starts_at.desc())
    if not _is_admin(current_user):
        query = query.where(Contest.is_published.is_(True))
    contests = list((await db.execute(query)).scalars().all())
    counts = await _participant_counts(db, [c.id for c in contests])
    mine = set((await db.execute(
        select(ContestRegistration.contest_id).where(ContestRegistration.user_id == current_user.id)
    )).scalars().all())
    now = _now()
    order = {"running": 0, "upcoming": 1, "ended": 2}
    items = [
        ContestSummary(**_summary(c, participants=counts.get(c.id, 0), registered=c.id in mine, now=now))
        for c in contests
    ]
    # Running first, then upcoming (soonest first), then past contests (most recent first).
    items.sort(key=lambda c: (order[c.phase], c.starts_at.timestamp() * (1 if c.phase == "upcoming" else -1)))
    return ContestList(items=items, server_time=now)


@router.get("/{slug}", response_model=ContestDetail)
async def get_contest(slug: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    contest = await _get_contest(db, slug, current_user)
    now = _now()
    registered = await _is_registered(db, contest.id, current_user.id)
    participants = (await _participant_counts(db, [contest.id])).get(contest.id, 0)
    problems: list[ContestProblemOut] = []
    if _phase(contest, now) != "upcoming" or _is_admin(current_user):
        mine = await _my_problem_status(db, contest, current_user.id)
        standings = await _standings(db, contest)
        solved_by = {cp.problem_id: sum(1 for s in standings if s.cells.get(cp.problem_id, _Cell()).solved) for cp in contest.problems}
        problems = [
            ContestProblemOut(
                label=_label(i), slug=cp.problem.slug, title=cp.problem.title, difficulty=cp.problem.difficulty,
                points=cp.points, status=mine.get(cp.problem_id, "todo"), solved_by=solved_by[cp.problem_id],
            )
            for i, cp in enumerate(contest.problems)
        ]
    return ContestDetail(
        **_summary(contest, participants=participants, registered=registered, now=now),
        description=contest.description, penalty_minutes=contest.penalty_minutes, server_time=now, problems=problems,
    )


@router.post("/{slug}/register", response_model=ContestSummary)
async def register(slug: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Register for a contest. Late registration is allowed until the contest ends."""
    contest = await _get_contest(db, slug, current_user)
    if _phase(contest) == "ended":
        raise HTTPException(status.HTTP_409_CONFLICT, "The contest has ended")
    if not await _is_registered(db, contest.id, current_user.id):
        db.add(ContestRegistration(contest_id=contest.id, user_id=current_user.id))
        try:
            await db.commit()
        except IntegrityError:  # registered concurrently
            await db.rollback()
    participants = (await _participant_counts(db, [contest.id])).get(contest.id, 0)
    return ContestSummary(**_summary(contest, participants=participants, registered=True, now=_now()))


@router.get("/{slug}/problems/{problem_slug}", response_model=ProblemDetail)
async def get_contest_problem(
    slug: str, problem_slug: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user),
):
    contest = await _get_contest(db, slug, current_user)
    _require_started(contest, current_user)
    _, cp = _contest_problem(contest, problem_slug)
    problem = await _get_problem(db, problem_slug, published_only=False)
    status_value = (await _my_problem_status(db, contest, current_user.id)).get(cp.problem_id, "todo")
    # Editorials stay hidden until the contest is over, then follow the practice rule (solved).
    show_editorial = _is_admin(current_user) or (_phase(contest) == "ended" and status_value == "solved")
    return problem_detail(problem, status_value, show_editorial=show_editorial)


@router.post(
    "/{slug}/problems/{problem_slug}/run",
    response_model=RunResponse,
    dependencies=[Depends(RateLimiter(30, 60, local_fallback=True, per_user=True))],
)
async def run_contest_problem(
    slug: str, problem_slug: str, payload: RunRequest,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user),
):
    """Run against the sample cases (plus optional custom input). Nothing is stored or scored."""
    contest = await _get_contest(db, slug, current_user)
    _require_started(contest, current_user)
    _contest_problem(contest, problem_slug)
    problem = await _get_problem(db, problem_slug, published_only=False)
    return await run_samples(problem, payload, current_user)


@router.post(
    "/{slug}/problems/{problem_slug}/submit",
    response_model=SubmitResponse,
    dependencies=[Depends(RateLimiter(10, 60, local_fallback=True, per_user=True))],
    responses={202: {"model": SubmitResponse, "description": "Queued: poll GET /api/practice/submissions/{id}"}},
)
async def submit_contest_problem(
    slug: str, problem_slug: str, payload: SubmitRequest,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user),
):
    """Submit during the contest window. Same judging and polling as practice submissions."""
    contest = await _get_contest(db, slug, current_user)
    phase = _phase(contest)
    if phase == "upcoming":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "The contest has not started yet")
    if phase == "ended":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "The contest has ended; submissions are closed")
    if not await _is_registered(db, contest.id, current_user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Register for the contest to submit")
    _contest_problem(contest, problem_slug)
    problem = await _get_problem(db, problem_slug, published_only=False)
    return await enqueue_submission(db, problem, payload, current_user, contest_id=contest.id)


@router.get("/{slug}/problems/{problem_slug}/submissions", response_model=list[SubmissionOut])
async def my_contest_problem_submissions(
    slug: str, problem_slug: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user),
):
    """Your submissions to one contest problem (same shape as the practice endpoint)."""
    contest = await _get_contest(db, slug, current_user)
    _, cp = _contest_problem(contest, problem_slug)
    rows = (await db.execute(
        select(PracticeSubmission)
        .where(
            PracticeSubmission.contest_id == contest.id,
            PracticeSubmission.problem_id == cp.problem_id,
            PracticeSubmission.user_id == current_user.id,
            PracticeSubmission.verdict != Verdict.SYSTEM_ERROR,
        )
        .order_by(PracticeSubmission.created_at.desc())
        .limit(50)
    )).scalars().all()
    return [SubmissionOut.model_validate(r) for r in rows]


@router.get("/{slug}/submissions", response_model=list[ContestSubmissionOut])
async def my_contest_submissions(slug: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    contest = await _get_contest(db, slug, current_user)
    labels = {cp.problem_id: (_label(i), cp.problem.slug) for i, cp in enumerate(contest.problems)}
    rows = (await db.execute(
        select(PracticeSubmission)
        .where(PracticeSubmission.contest_id == contest.id, PracticeSubmission.user_id == current_user.id)
        .order_by(PracticeSubmission.created_at.desc())
        .limit(200)
    )).scalars().all()
    return [
        ContestSubmissionOut(
            id=s.id, label=labels.get(s.problem_id, ("?", ""))[0], problem_slug=labels.get(s.problem_id, ("?", ""))[1],
            language=s.language, verdict=s.verdict, passed_count=s.passed_count, total_count=s.total_count,
            runtime_ms=s.runtime_ms, created_at=_utc(s.created_at),
        )
        for s in rows
    ]


@router.get("/{slug}/leaderboard", response_model=ContestLeaderboard)
async def leaderboard(slug: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    contest = await _get_contest(db, slug, current_user)
    phase = _phase(contest)
    labels = [_label(i) for i in range(len(contest.problems))]
    if phase == "upcoming" and not _is_admin(current_user):
        return ContestLeaderboard(contest_slug=contest.slug, phase=phase, labels=labels, rows=[])
    starts = _utc(contest.starts_at)
    rows: list[ContestLeaderboardRow] = []
    previous_key, rank = None, 0
    for position, s in enumerate(await _standings(db, contest), start=1):
        key = (s.score, s.penalty, s.last_accepted)
        if key != previous_key:
            rank, previous_key = position, key
        cells = []
        for i, cp in enumerate(contest.problems):
            cell = s.cells.get(cp.problem_id, _Cell())
            cells.append(LeaderboardCell(
                label=labels[i], solved=cell.solved, rejected=cell.rejected,
                solved_at_minutes=int((cell.solved_at - starts).total_seconds() // 60) if cell.solved_at else None,
            ))
        rows.append(ContestLeaderboardRow(
            rank=rank, user_id=s.user_id, name=s.name, score=s.score, solved=s.solved, penalty_minutes=s.penalty,
            problems=cells, is_me=s.user_id == current_user.id,
        ))
    return ContestLeaderboard(contest_slug=contest.slug, phase=phase, labels=labels, rows=rows)


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

admin_router = APIRouter(prefix="/admin/contests", tags=["Contests (Admin)"])


async def _admin_out(db: AsyncSession, contest_id: uuid.UUID) -> ContestAdminOut:
    contest = (await db.execute(
        select(Contest)
        .options(selectinload(Contest.problems).selectinload(ContestProblem.problem))
        .where(Contest.id == contest_id)
        .execution_options(populate_existing=True)
    )).scalar_one_or_none()
    if contest is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contest not found")
    starts, ends = _utc(contest.starts_at), _utc(contest.ends_at)
    return ContestAdminOut(
        id=contest.id, slug=contest.slug, title=contest.title, description=contest.description,
        starts_at=starts, ends_at=ends, duration_minutes=int((ends - starts).total_seconds() // 60),
        penalty_minutes=contest.penalty_minutes, is_published=contest.is_published, phase=_phase(contest),
        participants=(await _participant_counts(db, [contest.id])).get(contest.id, 0),
        problems=[
            ContestAdminProblem(
                problem_id=cp.problem_id, points=cp.points, label=_label(i), slug=cp.problem.slug,
                title=cp.problem.title, difficulty=cp.problem.difficulty, is_published=cp.problem.is_published,
            )
            for i, cp in enumerate(contest.problems)
        ],
    )


async def _apply(db: AsyncSession, contest: Contest, payload: ContestUpsert) -> None:
    clash = (await db.execute(select(Contest.id).where(Contest.slug == payload.slug, Contest.id != contest.id))).first()
    if clash:
        raise HTTPException(status.HTTP_409_CONFLICT, "Another contest already uses this slug")
    found = set((await db.execute(
        select(PracticeProblem.id).where(PracticeProblem.id.in_([p.problem_id for p in payload.problems]))
    )).scalars().all())
    missing = [str(p.problem_id) for p in payload.problems if p.problem_id not in found]
    if missing:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unknown problem id(s): {', '.join(missing)}")
    starts = _utc(payload.starts_at)
    contest.slug, contest.title, contest.description = payload.slug, payload.title, payload.description
    contest.starts_at, contest.ends_at = starts, starts + timedelta(minutes=payload.duration_minutes)
    contest.penalty_minutes, contest.is_published = payload.penalty_minutes, payload.is_published
    # Reuse existing rows: the unit of work inserts before it deletes, so replacing a row with an
    # identical (contest, problem) pair would trip the unique constraint.
    existing = {cp.problem_id: cp for cp in contest.problems}
    rows = []
    for i, p in enumerate(payload.problems):
        row = existing.get(p.problem_id) or ContestProblem(problem_id=p.problem_id)
        row.points, row.order_index = p.points, i
        rows.append(row)
    contest.problems = rows


@admin_router.get("", response_model=list[ContestAdminOut])
async def admin_list(db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles(_ADMIN))):
    ids = (await db.execute(select(Contest.id).order_by(Contest.starts_at.desc()))).scalars().all()
    return [await _admin_out(db, cid) for cid in ids]


@admin_router.get("/{contest_id}", response_model=ContestAdminOut)
async def admin_get(contest_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles(_ADMIN))):
    return await _admin_out(db, contest_id)


@admin_router.post("", response_model=ContestAdminOut, status_code=status.HTTP_201_CREATED)
async def admin_create(payload: ContestUpsert, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles(_ADMIN))):
    contest = Contest(created_by=current_user.id, problems=[])
    await _apply(db, contest, payload)
    db.add(contest)
    await log_audit_event(db=db, action="CONTEST_CREATED", resource_type="contest", resource_id=payload.slug,
                          details={"title": payload.title}, user_id=current_user.id, institution_id=current_user.institution_id)
    await db.commit()
    return await _admin_out(db, contest.id)


@admin_router.put("/{contest_id}", response_model=ContestAdminOut)
async def admin_update(
    contest_id: uuid.UUID, payload: ContestUpsert,
    db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles(_ADMIN)),
):
    contest = (await db.execute(
        select(Contest).options(selectinload(Contest.problems)).where(Contest.id == contest_id)
    )).scalar_one_or_none()
    if contest is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contest not found")
    if _phase(contest) != "upcoming":
        # Changing the problems, points or window of a started contest would rewrite results.
        same_problems = [(cp.problem_id, cp.points) for cp in contest.problems] == [(p.problem_id, p.points) for p in payload.problems]
        same_window = _utc(contest.starts_at) == _utc(payload.starts_at) and \
            _utc(contest.ends_at) == _utc(payload.starts_at) + timedelta(minutes=payload.duration_minutes)
        if not (same_problems and same_window and contest.penalty_minutes == payload.penalty_minutes):
            raise HTTPException(status.HTTP_409_CONFLICT, "Problems, points, timing and penalty are fixed once the contest starts")
    await _apply(db, contest, payload)
    await log_audit_event(db=db, action="CONTEST_UPDATED", resource_type="contest", resource_id=str(contest_id),
                          details={"title": payload.title}, user_id=current_user.id, institution_id=current_user.institution_id)
    await db.commit()
    return await _admin_out(db, contest.id)


@admin_router.delete("/{contest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete(contest_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(require_roles(_ADMIN))):
    contest = await db.get(Contest, contest_id)
    if contest is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contest not found")
    await db.delete(contest)
    await log_audit_event(db=db, action="CONTEST_DELETED", resource_type="contest", resource_id=str(contest_id),
                          details={"title": contest.title}, user_id=current_user.id, institution_id=current_user.institution_id)
    await db.commit()
