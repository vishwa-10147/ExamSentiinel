"""Practice platform: judge verdict logic, harness generation and API behaviour.

Sandbox calls are faked so these run without a code-execution engine. The
final test exercises the real Piston engine and is skipped when it is not
reachable (see docker-compose.piston.yml).
"""

import json
from types import SimpleNamespace

import httpx
import pytest
from httpx import AsyncClient

from app.models.practice import JudgeMode, Verdict
from app.models.user import User, UserRole
from app.services import practice_judge
from app.services.practice_judge import (
    INPUT_FILE,
    RESULT_MARKER,
    JudgeCase,
    JudgeSpecError,
    build_harness,
    normalize_function_input,
    outputs_match,
    starter_code,
    validate_function_spec,
)
from app.services.sandbox_service import SandboxResult

from tests.test_exam_engine import auth_header

SPEC = {"name": "addUp", "params": [{"name": "nums", "type": "int[]"}, {"name": "k", "type": "int"}], "return_type": "int"}


def _problem(**overrides):
    base = dict(judge_mode=JudgeMode.FUNCTION, function_spec=SPEC, compare_mode="exact", time_limit_ms=2000, memory_limit_mb=256)
    base.update(overrides)
    return SimpleNamespace(**base)


def _records(*recs: dict) -> str:
    return "".join(RESULT_MARKER + json.dumps(r) + "\n" for r in recs)


@pytest.fixture
def fake_sandbox(monkeypatch):
    """Replace the engine call; tests set ``fake.result`` and inspect ``fake.calls``."""
    fake = SimpleNamespace(result=None, calls=[])

    async def execute_async(language, source_code, stdin, timeout_sec, memory_mb, database_setup="", extra_files=None):
        fake.calls.append(SimpleNamespace(language=language, source=source_code, stdin=stdin, files=extra_files or {}))
        return fake.result

    monkeypatch.setattr(practice_judge.sandbox_service, "execute_async", execute_async)
    return fake


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def test_validate_function_spec_rejects_bad_types_and_names():
    validate_function_spec(SPEC)
    with pytest.raises(JudgeSpecError):
        validate_function_spec({**SPEC, "return_type": "dict"})
    with pytest.raises(JudgeSpecError):
        validate_function_spec({**SPEC, "name": "not valid"})
    with pytest.raises(JudgeSpecError):
        validate_function_spec(None)


def test_normalize_function_input_checks_line_count_and_json():
    assert normalize_function_input("[1, 2,  3]\n 4 ", SPEC) == "[1,2,3]\n4"
    with pytest.raises(JudgeSpecError):
        normalize_function_input("[1,2,3]", SPEC)  # missing k
    with pytest.raises(JudgeSpecError):
        normalize_function_input("[1,2\n4", SPEC)  # invalid JSON


def test_outputs_match_modes():
    assert outputs_match([0, 1], [0, 1], "exact")
    assert not outputs_match([1, 0], [0, 1], "exact")
    assert outputs_match([1, 0], [0, 1], "unordered")
    assert outputs_match(2.500001, 2.5, "float")
    assert not outputs_match(2.6, 2.5, "float")
    assert outputs_match(2, 2.0, "exact")
    assert not outputs_match(True, 1, "exact"), "JSON true must not equal 1"


@pytest.mark.parametrize("language", ["python", "javascript", "java", "cpp"])
def test_harness_reads_input_file_and_wraps_student_code(language):
    code = starter_code(SPEC, language)
    harness = build_harness(code, SPEC, language)
    assert INPUT_FILE in harness
    assert RESULT_MARKER in harness
    assert "addUp" in harness
    if language == "java":
        # Java's single-file launcher runs the first class: Main must precede Solution.
        assert harness.index("public class Main") < harness.index("class Solution")


def test_java_harness_hoists_student_imports():
    code = "import java.util.HashMap;\nclass Solution { public int addUp(int[] nums, int k) { return k; } }"
    harness = build_harness(code, SPEC, "java")
    assert harness.index("import java.util.HashMap;") < harness.index("public class Main")


# ---------------------------------------------------------------------------
# Verdicts
# ---------------------------------------------------------------------------

CASES = [JudgeCase("[1,2]\n3", "6"), JudgeCase("[5]\n0", "5", is_sample=False)]


async def test_accepted_sends_data_as_file_not_stdin(fake_sandbox):
    fake_sandbox.result = SandboxResult("success", _records(
        {"i": 0, "ok": True, "result": 6, "ms": 1.2, "stdout": "dbg\n"},
        {"i": 1, "ok": True, "result": 5, "ms": 0.4, "stdout": ""},
    ), "", 0, 50)
    outcome = await practice_judge.judge(_problem(), "python", "code", CASES)
    assert outcome.verdict == Verdict.ACCEPTED
    assert outcome.passed_count == 2
    assert outcome.cases[0].stdout == "dbg\n"
    call = fake_sandbox.calls[0]
    assert call.stdin == ""
    assert call.files[INPUT_FILE].splitlines() == ["2", "[1,2]", "3", "[5]", "0"]


async def test_wrong_answer_stops_at_first_failure(fake_sandbox):
    fake_sandbox.result = SandboxResult("success", _records(
        {"i": 0, "ok": True, "result": 7, "ms": 1, "stdout": ""},
        {"i": 1, "ok": True, "result": 5, "ms": 1, "stdout": ""},
    ), "", 0, 50)
    outcome = await practice_judge.judge(_problem(), "python", "code", CASES, stop_on_failure=True)
    assert outcome.verdict == Verdict.WRONG_ANSWER
    assert outcome.failed_index == 0
    assert len(outcome.cases) == 1


async def test_runtime_error_in_case(fake_sandbox):
    fake_sandbox.result = SandboxResult("success", _records(
        {"i": 0, "ok": False, "error": "IndexError: list index out of range", "ms": 1, "stdout": ""},
    ), "", 0, 50)
    outcome = await practice_judge.judge(_problem(), "python", "code", CASES, stop_on_failure=True)
    assert outcome.verdict == Verdict.RUNTIME_ERROR
    assert "IndexError" in outcome.error


@pytest.mark.parametrize(
    ("status", "expected"),
    [("timeout", Verdict.TIME_LIMIT_EXCEEDED), ("memory_limit", Verdict.MEMORY_LIMIT_EXCEEDED),
     ("output_limit", Verdict.OUTPUT_LIMIT_EXCEEDED), ("error", Verdict.RUNTIME_ERROR)],
)
async def test_process_killed_mid_run(fake_sandbox, status, expected):
    # First case finished, then the process died before reporting the second.
    fake_sandbox.result = SandboxResult(status, _records({"i": 0, "ok": True, "result": 6, "ms": 1, "stdout": ""}), "killed", 137, 50)
    outcome = await practice_judge.judge(_problem(), "python", "code", CASES)
    assert outcome.verdict == expected
    assert outcome.failed_index == 1
    assert outcome.passed_count == 1


async def test_slow_case_is_time_limit_exceeded(fake_sandbox):
    fake_sandbox.result = SandboxResult("success", _records(
        {"i": 0, "ok": True, "result": 6, "ms": 2500, "stdout": ""},
        {"i": 1, "ok": True, "result": 5, "ms": 1, "stdout": ""},
    ), "", 0, 50)
    outcome = await practice_judge.judge(_problem(), "python", "code", CASES)
    assert outcome.verdict == Verdict.TIME_LIMIT_EXCEEDED
    assert outcome.failed_index == 0


async def test_compile_errors_including_java_launcher(fake_sandbox):
    fake_sandbox.result = SandboxResult("compile_error", "", "main.cpp:1: error: x", 1, 50, "main.cpp:1: error: x\nchmod: cannot access 'a.out'")
    outcome = await practice_judge.judge(_problem(), "cpp", "code", CASES)
    assert outcome.verdict == Verdict.COMPILE_ERROR
    assert "chmod" not in outcome.compile_output

    fake_sandbox.result = SandboxResult("error", "", "Main.java:3: error: ';' expected\n1 error\nerror: compilation failed", 1, 50)
    outcome = await practice_judge.judge(_problem(), "java", "code", CASES)
    assert outcome.verdict == Verdict.COMPILE_ERROR
    assert "';' expected" in outcome.compile_output


async def test_engine_outage_is_system_error(fake_sandbox):
    fake_sandbox.result = SandboxResult("system_error", "", "engine down", -1, 5)
    outcome = await practice_judge.judge(_problem(), "python", "code", CASES)
    assert outcome.verdict == Verdict.SYSTEM_ERROR


async def test_stdio_mode_runs_each_case_and_compares_text(fake_sandbox):
    fake_sandbox.result = SandboxResult("success", "6  \n", "", 0, 20)
    problem = _problem(judge_mode=JudgeMode.STDIO, function_spec=None)
    outcome = await practice_judge.judge(problem, "c", "code", [JudgeCase("1 2 3\n", "6"), JudgeCase("2 4\n", "6", False)])
    assert outcome.verdict == Verdict.ACCEPTED
    assert [c.stdin for c in fake_sandbox.calls] == ["1 2 3\n", "2 4\n"]


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

PROBLEM_PAYLOAD = {
    "slug": "add-up",
    "title": "Add Up",
    "difficulty": "EASY",
    "tags": ["math"],
    "statement": "Return the sum of `nums` plus `k`.",
    "judge_mode": "FUNCTION",
    "function_spec": SPEC,
    "reference_solution": {"language": "python", "code": "class Solution:\n    def addUp(self, nums, k):\n        return sum(nums) + k\n"},
    "is_published": True,
    "test_cases": [
        {"input_data": "[1, 2]\n3", "expected_output": "6", "is_sample": True, "explanation": "1 + 2 + 3"},
        {"input_data": "[100]\n-1", "expected_output": "99", "is_sample": False},
    ],
}


def _user(users: list[User], role: UserRole) -> User:
    return next(u for u in users if u.role == role)


async def test_admin_creates_problem_and_students_never_see_hidden_tests(async_client: AsyncClient, seed_users):
    admin, candidate = _user(seed_users, UserRole.ADMIN), _user(seed_users, UserRole.CANDIDATE)

    r = await async_client.post("/api/practice/admin/problems", headers=auth_header(candidate), json=PROBLEM_PAYLOAD)
    assert r.status_code == 403

    r = await async_client.post("/api/practice/admin/problems", headers=auth_header(admin), json=PROBLEM_PAYLOAD)
    assert r.status_code == 201, r.text
    assert r.json()["test_cases"][0]["input_data"] == "[1,2]\n3"  # normalised

    r = await async_client.post("/api/practice/admin/problems", headers=auth_header(admin), json=PROBLEM_PAYLOAD)
    assert r.status_code == 409  # duplicate slug

    detail = (await async_client.get("/api/practice/problems/add-up", headers=auth_header(candidate))).json()
    assert [e["expected_output"] for e in detail["examples"]] == ["6"]
    assert "test_cases" not in detail and "reference_solution" not in detail
    assert detail["has_reference_solution"] is True
    body = json.dumps(detail)
    assert "[100]" not in body and "sum(nums)" not in body  # hidden input / reference code never sent
    assert set(detail["starter_code"]) == {"python", "javascript", "java", "cpp"}


async def test_admin_rejects_malformed_tests(async_client: AsyncClient, seed_users):
    admin = _user(seed_users, UserRole.ADMIN)
    bad = {**PROBLEM_PAYLOAD, "slug": "bad", "test_cases": [{"input_data": "[1,2]", "expected_output": "3", "is_sample": True}]}
    r = await async_client.post("/api/practice/admin/problems", headers=auth_header(admin), json=bad)
    assert r.status_code == 422
    assert "input line" in r.json()["detail"]


async def test_unpublished_problems_are_hidden_from_students(async_client: AsyncClient, seed_users):
    admin, candidate = _user(seed_users, UserRole.ADMIN), _user(seed_users, UserRole.CANDIDATE)
    await async_client.post("/api/practice/admin/problems", headers=auth_header(admin), json={**PROBLEM_PAYLOAD, "is_published": False})
    listing = (await async_client.get("/api/practice/problems", headers=auth_header(candidate))).json()
    assert listing["total"] == 0
    assert (await async_client.get("/api/practice/problems/add-up", headers=auth_header(candidate))).status_code == 404


async def test_submit_records_submission_and_hides_hidden_failure(async_client: AsyncClient, seed_users, fake_sandbox):
    admin, candidate = _user(seed_users, UserRole.ADMIN), _user(seed_users, UserRole.CANDIDATE)
    await async_client.post("/api/practice/admin/problems", headers=auth_header(admin), json=PROBLEM_PAYLOAD)
    headers = auth_header(candidate)

    # Fails the hidden case: its input/expected must not be revealed.
    fake_sandbox.result = SandboxResult("success", _records(
        {"i": 0, "ok": True, "result": 6, "ms": 1, "stdout": ""},
        {"i": 1, "ok": True, "result": 0, "ms": 1, "stdout": ""},
    ), "", 0, 10)
    r = await async_client.post("/api/practice/problems/add-up/submit", headers=headers, json={"language": "python", "code": "x"})
    assert r.status_code == 200, r.text
    sub = r.json()
    assert sub["verdict"] == "WRONG_ANSWER"
    assert sub["failure"]["case_number"] == 2 and sub["failure"]["is_sample"] is False
    assert sub["failure"]["input"] is None and sub["failure"]["expected"] is None

    fake_sandbox.result = SandboxResult("success", _records(
        {"i": 0, "ok": True, "result": 6, "ms": 1, "stdout": ""},
        {"i": 1, "ok": True, "result": 99, "ms": 1, "stdout": ""},
    ), "", 0, 10)
    r = await async_client.post("/api/practice/problems/add-up/submit", headers=headers, json={"language": "python", "code": "y"})
    assert r.json()["verdict"] == "ACCEPTED"

    subs = (await async_client.get("/api/practice/problems/add-up/submissions", headers=headers)).json()
    assert [s["verdict"] for s in subs] == ["ACCEPTED", "WRONG_ANSWER"]

    stats = (await async_client.get("/api/practice/stats/me", headers=headers)).json()
    assert stats["solved_total"] == 1 and stats["by_difficulty"]["EASY"] == {"solved": 1, "total": 1}
    assert stats["acceptance_rate"] == 50.0 and stats["current_streak_days"] == 1

    listing = (await async_client.get("/api/practice/problems", headers=headers)).json()
    assert listing["items"][0]["status"] == "solved"
    board = (await async_client.get("/api/practice/leaderboard", headers=headers)).json()
    assert board[0]["solved"] == 1

    # Another student's submissions are private.
    other = (await async_client.get("/api/practice/problems/add-up/submissions", headers=auth_header(admin))).json()
    assert other == []


async def test_engine_outage_is_not_recorded_as_attempt(async_client: AsyncClient, seed_users, fake_sandbox):
    admin, candidate = _user(seed_users, UserRole.ADMIN), _user(seed_users, UserRole.CANDIDATE)
    await async_client.post("/api/practice/admin/problems", headers=auth_header(admin), json=PROBLEM_PAYLOAD)
    fake_sandbox.result = SandboxResult("system_error", "", "down", -1, 1)
    r = await async_client.post("/api/practice/problems/add-up/submit", headers=auth_header(candidate), json={"language": "python", "code": "x"})
    assert r.json()["verdict"] == "SYSTEM_ERROR"
    subs = (await async_client.get("/api/practice/problems/add-up/submissions", headers=auth_header(candidate))).json()
    assert subs == []


async def test_sandbox_playground_requires_login(async_client: AsyncClient):
    r = await async_client.post("/api/sandbox/execute", json={"language": "python", "code": "print(1)"})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Real engine (skipped when Piston isn't running)
# ---------------------------------------------------------------------------

def _piston_available() -> bool:
    try:
        return httpx.get("http://localhost:2000/api/v2/runtimes", timeout=1).status_code == 200
    except httpx.HTTPError:
        return False


@pytest.mark.skipif(not _piston_available(), reason="Piston engine not running (docker compose -f docker-compose.piston.yml up -d)")
@pytest.mark.parametrize(
    ("language", "code"),
    [
        ("python", "class Solution:\n    def addUp(self, nums, k):\n        return sum(nums) + k\n"),
        ("javascript", "class Solution { addUp(nums, k) { return nums.reduce((a, b) => a + b, 0) + k; } }\n"),
        ("java", "class Solution { public int addUp(int[] nums, int k) { int s = k; for (int x : nums) s += x; return s; } }\n"),
        ("cpp", "class Solution { public: int addUp(vector<int>& nums, int k) { int s = k; for (int x : nums) s += x; return s; } };\n"),
    ],
)
async def test_real_engine_accepts_correct_solutions(language, code):
    outcome = await practice_judge.judge(_problem(), language, code, [JudgeCase("[1,2]\n3", "6"), JudgeCase("[]\n-4", "-4")])
    assert outcome.verdict == Verdict.ACCEPTED, (outcome.compile_output, outcome.error)
