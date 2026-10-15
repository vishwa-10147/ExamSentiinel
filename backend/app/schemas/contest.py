import uuid
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.practice import ProblemDifficulty, Verdict

ContestPhase = Literal["upcoming", "running", "ended"]
ProblemStatus = Literal["solved", "attempted", "todo"]


class ContestSummary(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    starts_at: datetime
    ends_at: datetime
    duration_minutes: int
    phase: ContestPhase
    problem_count: int
    participants: int
    registered: bool
    is_published: bool


class ContestProblemOut(BaseModel):
    label: str  # "A", "B", ...
    slug: str
    title: str
    difficulty: ProblemDifficulty
    points: int
    status: ProblemStatus = "todo"
    solved_by: int = 0


class ContestDetail(ContestSummary):
    description: str
    penalty_minutes: int
    server_time: datetime
    # Empty until the contest starts (admins always see them).
    problems: List[ContestProblemOut]


class ContestList(BaseModel):
    items: List[ContestSummary]
    server_time: datetime


class LeaderboardCell(BaseModel):
    label: str
    solved: bool
    rejected: int  # rejected attempts (before the accepted one, if any)
    solved_at_minutes: Optional[int] = None


class ContestLeaderboardRow(BaseModel):
    rank: int
    user_id: uuid.UUID
    name: str
    score: int
    solved: int
    penalty_minutes: int
    problems: List[LeaderboardCell]
    is_me: bool = False


class ContestLeaderboard(BaseModel):
    contest_slug: str
    phase: ContestPhase
    labels: List[str]
    rows: List[ContestLeaderboardRow]


class ContestSubmissionOut(BaseModel):
    id: uuid.UUID
    label: str
    problem_slug: str
    language: str
    verdict: Verdict
    passed_count: int
    total_count: int
    runtime_ms: Optional[int]
    created_at: datetime


# ---- Admin -----------------------------------------------------------------

class ContestProblemIn(BaseModel):
    problem_id: uuid.UUID
    points: int = Field(default=100, ge=1, le=10_000)


class ContestUpsert(BaseModel):
    slug: str = Field(min_length=3, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(default="", max_length=20_000)
    starts_at: datetime
    duration_minutes: int = Field(ge=5, le=7 * 24 * 60)
    penalty_minutes: int = Field(default=5, ge=0, le=60)
    is_published: bool = False
    problems: List[ContestProblemIn] = Field(min_length=1, max_length=26)

    @field_validator("problems")
    @classmethod
    def _unique_problems(cls, value: List[ContestProblemIn]) -> List[ContestProblemIn]:
        if len({p.problem_id for p in value}) != len(value):
            raise ValueError("A problem can appear only once in a contest")
        return value


class ContestAdminProblem(ContestProblemIn):
    label: str
    slug: str
    title: str
    difficulty: ProblemDifficulty
    is_published: bool  # in practice; unpublished problems stay contest-only


class ContestAdminOut(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    description: str
    starts_at: datetime
    ends_at: datetime
    duration_minutes: int
    penalty_minutes: int
    is_published: bool
    phase: ContestPhase
    participants: int
    problems: List[ContestAdminProblem]
