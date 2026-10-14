import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.practice import JudgeMode, ProblemDifficulty, Verdict

Language = Literal["python", "javascript", "java", "cpp", "c", "sql"]


class FunctionParam(BaseModel):
    name: str
    type: str
    # Internal params are part of the test input (e.g. a cycle position) but not passed to the method.
    internal: bool = False


class FunctionSpec(BaseModel):
    name: str
    params: List[FunctionParam]
    return_type: str
    cycle: Optional[Dict[str, str]] = None  # {"list": <ListNode param>, "pos": <int param>}


class ExampleCase(BaseModel):
    input: str
    expected_output: str
    explanation: Optional[str] = None


# ---- Student-facing --------------------------------------------------------

class ProblemListItem(BaseModel):
    id: uuid.UUID
    number: Optional[int] = None  # stable public ID
    topic: Optional[str] = None
    slug: str
    title: str
    difficulty: ProblemDifficulty
    tags: List[str]
    acceptance_rate: Optional[float] = None  # % of submissions accepted
    status: Literal["solved", "attempted", "todo"] = "todo"


class ProblemList(BaseModel):
    items: List[ProblemListItem]
    total: int


class ProblemDetail(BaseModel):
    id: uuid.UUID
    number: Optional[int] = None
    topic: Optional[str] = None
    slug: str
    title: str
    difficulty: ProblemDifficulty
    tags: List[str]
    statement: str
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    constraints: Optional[str]
    complexity: Optional[str] = None
    # The editorial is only returned once the user has solved the problem (or to admins).
    editorial: Optional[str] = None
    has_editorial: bool = False
    hints: List[str]
    judge_mode: JudgeMode
    function_spec: Optional[FunctionSpec]
    sql_schema: Optional[str] = None
    compare_mode: str = "exact"
    examples: List[ExampleCase]
    starter_code: Dict[str, str]
    languages: List[str]
    time_limit_ms: int
    memory_limit_mb: int
    status: Literal["solved", "attempted", "todo"] = "todo"
    has_reference_solution: bool = False


class RunRequest(BaseModel):
    language: Language
    code: str = Field(min_length=1, max_length=50_000)
    # Optional extra input (FUNCTION mode: one JSON value per parameter line).
    custom_input: Optional[str] = Field(default=None, max_length=20_000)


class SubmitRequest(BaseModel):
    language: Language
    code: str = Field(min_length=1, max_length=50_000)


class CaseResultOut(BaseModel):
    index: int
    passed: Optional[bool]
    input: Optional[str] = None
    expected: Optional[str] = None
    output: Optional[str] = None
    stdout: str = ""
    runtime_ms: Optional[float] = None
    error: Optional[str] = None
    is_custom: bool = False


class RunResponse(BaseModel):
    verdict: Verdict
    cases: List[CaseResultOut]
    passed_count: int
    total_count: int
    runtime_ms: Optional[int]
    compile_output: Optional[str] = None
    error: Optional[str] = None


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    problem_id: uuid.UUID
    language: str
    verdict: Verdict
    passed_count: int
    total_count: int
    runtime_ms: Optional[int]
    failure: Optional[Dict[str, Any]]
    created_at: datetime
    source_code: Optional[str] = None


class SubmitResponse(SubmissionOut):
    compile_output: Optional[str] = None


class DifficultyProgress(BaseModel):
    solved: int
    total: int


class PracticeStats(BaseModel):
    solved_total: int
    problems_total: int
    by_difficulty: Dict[str, DifficultyProgress]
    submissions_total: int
    accepted_total: int
    acceptance_rate: Optional[float]
    current_streak_days: int
    activity: Dict[str, int]  # ISO date -> submissions that day (last 365 days)
    recent: List[Dict[str, Any]]
    by_topic: List["TopicProgress"] = []


class TopicProgress(BaseModel):
    topic: str
    solved: int
    attempted: int
    total: int


class SubmissionHistoryItem(BaseModel):
    id: uuid.UUID
    problem_number: Optional[int]
    problem_slug: str
    problem_title: str
    language: str
    verdict: Verdict
    passed_count: int
    total_count: int
    runtime_ms: Optional[int]
    created_at: datetime


class SubmissionHistory(BaseModel):
    items: List[SubmissionHistoryItem]
    total: int


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: uuid.UUID
    name: str
    solved: int
    easy: int
    medium: int
    hard: int


# ---- Admin ---------------------------------------------------------------

class TestCaseIn(BaseModel):
    input_data: str
    expected_output: str
    is_sample: bool = False
    explanation: Optional[str] = None


class TestCaseOut(TestCaseIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    order_index: int


class ProblemUpsert(BaseModel):
    # Unknown fields (including any attempt to send a "checker") are ignored: checkers
    # run inside the API process, so they can only come from the repository's bank.
    slug: str = Field(min_length=2, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    number: Optional[int] = Field(default=None, ge=1, le=99_999)
    topic: Optional[str] = Field(default=None, max_length=64)
    title: str = Field(min_length=2, max_length=255)
    difficulty: ProblemDifficulty
    tags: List[str] = []
    statement: str = Field(min_length=10)
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    constraints: Optional[str] = None
    complexity: Optional[str] = Field(default=None, max_length=255)
    editorial: Optional[str] = None
    hints: List[str] = []
    judge_mode: JudgeMode = JudgeMode.FUNCTION
    function_spec: Optional[FunctionSpec] = None
    sql_schema: Optional[str] = None
    # "checker" is only valid for problems that already have a bank-provided checker.
    compare_mode: Literal["exact", "unordered", "float", "checker"] = "exact"
    starter_code: Dict[str, str] = {}
    reference_solution: Optional[Dict[str, str]] = None
    time_limit_ms: int = Field(default=2000, ge=100, le=10_000)
    memory_limit_mb: int = Field(default=256, ge=32, le=512)
    is_published: bool = False
    test_cases: List[TestCaseIn] = Field(default_factory=list)


class ProblemAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: Optional[int] = None
    topic: Optional[str] = None
    slug: str
    title: str
    difficulty: ProblemDifficulty
    tags: List[str]
    statement: str
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    constraints: Optional[str]
    complexity: Optional[str] = None
    editorial: Optional[str] = None
    hints: List[str]
    judge_mode: JudgeMode
    function_spec: Optional[Dict[str, Any]]
    sql_schema: Optional[str] = None
    compare_mode: str
    starter_code: Dict[str, str]
    reference_solution: Optional[Dict[str, str]]
    time_limit_ms: int
    memory_limit_mb: int
    is_published: bool
    test_cases: List[TestCaseOut]
    created_at: datetime
    updated_at: datetime


class ProblemAdminListItem(BaseModel):
    id: uuid.UUID
    number: Optional[int] = None
    topic: Optional[str] = None
    slug: str
    title: str
    difficulty: ProblemDifficulty
    tags: List[str]
    is_published: bool
    test_case_count: int
    sample_count: int
    submissions: int
    acceptance_rate: Optional[float]
    # Set when real acceptance (20+ submissions) suggests a different level.
    suggested_difficulty: Optional[ProblemDifficulty] = None
    updated_at: datetime


class ValidationReport(BaseModel):
    ok: bool
    verdict: Verdict
    passed_count: int
    total_count: int
    message: str
    failures: List[CaseResultOut] = []


PracticeStats.model_rebuild()
