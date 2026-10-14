"""Practice API features for the DSA bank: IDs, topics, sorting, editorials, checkers,
submission history, progress and the code playground. The engine is faked here."""

import json

import pytest_asyncio
from httpx import AsyncClient

from app.models.practice import JudgeMode, PracticeProblem, PracticeTestCase, ProblemDifficulty
from app.models.user import UserRole
from app.services.sandbox_service import SandboxResult
from tests.test_exam_engine import auth_header
from tests.test_practice import PROBLEM_PAYLOAD, _records, _user, fake_sandbox  # noqa: F401  (fixture)

@pytest_asyncio.fixture
async def db_session():
    from tests.conftest import test_async_session_maker

    async with test_async_session_maker() as session:
        yield session


TOPO_CHECKER ="def check(args, output, expected):\n    n, edges = args\n    pos = {v: i for i, v in enumerate(output)}\n    return sorted(output) == list(range(n)) and all(pos[u] < pos[v] for u, v in edges)\n"


async def _add_bank_problems(db_session):
    """Insert problems the way the seeder does (the admin API cannot set a checker)."""
    spec = {"name": "taskOrder", "params": [{"name": "n", "type": "int"}, {"name": "deps", "type": "int[][]"}], "return_type": "int[]"}
    rows = [
        PracticeProblem(
            slug="task-ordering", number=111, topic="Graphs", title="Order the Tasks", difficulty=ProblemDifficulty.MEDIUM,
            tags=["graph"], statement="Return any valid order of the tasks.", constraints="- small", complexity="O(n + e)",
            editorial="Kahn's algorithm SECRET-EDITORIAL", hints=[], judge_mode=JudgeMode.FUNCTION, function_spec=spec,
            compare_mode="checker", checker=TOPO_CHECKER, starter_code={},
            reference_solution={"language": "python", "code": "class Solution:\n    def taskOrder(self, n, deps):\n        return list(range(n))\n"},
            time_limit_ms=2000, memory_limit_mb=256, is_published=True,
            test_cases=[
                PracticeTestCase(input_data="2\n[]", expected_output="[0,1]", is_sample=True, order_index=0),
                PracticeTestCase(input_data="3\n[[2,0],[0,1]]", expected_output="[2,0,1]", is_sample=False, order_index=1),
            ],
        ),
        PracticeProblem(
            slug="lone-value", number=116, topic="Bit Manipulation", title="The Lone Value", difficulty=ProblemDifficulty.EASY,
            tags=["xor"], statement="Every value appears twice except one.", constraints="- small", complexity="O(n)",
            editorial="XOR everything.", hints=[], judge_mode=JudgeMode.FUNCTION,
            function_spec={"name": "loneValue", "params": [{"name": "nums", "type": "int[]"}], "return_type": "int"},
            compare_mode="exact", starter_code={}, reference_solution={"language": "python", "code": "x"},
            time_limit_ms=2000, memory_limit_mb=256, is_published=True,
            test_cases=[PracticeTestCase(input_data="[2,2,1]", expected_output="1", is_sample=True, order_index=0)],
        ),
        PracticeProblem(
            slug="pair-with-target-sum", number=1, topic="Hashing", title="Pair With Target Sum", difficulty=ProblemDifficulty.EASY,
            tags=["hash-table"], statement="Find two indices.", constraints="- small", hints=[], judge_mode=JudgeMode.FUNCTION,
            function_spec={"name": "twoSum", "params": [{"name": "nums", "type": "int[]"}], "return_type": "int"},
            compare_mode="exact", starter_code={}, reference_solution=None, time_limit_ms=2000, memory_limit_mb=256, is_published=True,
            test_cases=[PracticeTestCase(input_data="[1]", expected_output="1", is_sample=True, order_index=0)],
        ),
    ]
    db_session.add_all(rows)
    await db_session.commit()


async def test_listing_has_ids_topics_filters_and_sorting(async_client: AsyncClient, seed_users, db_session):
    await _add_bank_problems(db_session)
    headers = auth_header(_user(seed_users, UserRole.CANDIDATE))

    items = (await async_client.get("/api/practice/problems", headers=headers)).json()["items"]
    assert [p["number"] for p in items] == [1, 111, 116]  # default: by ID
    assert items[1]["topic"] == "Graphs"

    by_diff = (await async_client.get("/api/practice/problems?sort=difficulty", headers=headers)).json()["items"]
    assert [p["number"] for p in by_diff] == [1, 116, 111]  # Easy (by ID), then Medium

    graphs = (await async_client.get("/api/practice/problems?topic=Graphs", headers=headers)).json()
    assert graphs["total"] == 1 and graphs["items"][0]["slug"] == "task-ordering"

    by_id = (await async_client.get("/api/practice/problems?search=%23116", headers=headers)).json()["items"]
    assert [p["slug"] for p in by_id] == ["lone-value"]

    assert (await async_client.get("/api/practice/problems?sort=bogus", headers=headers)).status_code == 422

    topics = (await async_client.get("/api/practice/topics", headers=headers)).json()
    assert [t["topic"] for t in topics] == ["Hashing", "Graphs", "Bit Manipulation"]  # syllabus order
    assert all(t["total"] == 1 and t["solved"] == 0 for t in topics)


async def test_detail_exposes_formats_but_never_checker_or_unearned_editorial(async_client: AsyncClient, seed_users, db_session, fake_sandbox):
    await _add_bank_problems(db_session)
    candidate, admin = _user(seed_users, UserRole.CANDIDATE), _user(seed_users, UserRole.ADMIN)
    headers = auth_header(candidate)

    detail = (await async_client.get("/api/practice/problems/task-ordering", headers=headers)).json()
    assert detail["number"] == 111 and detail["topic"] == "Graphs" and detail["complexity"] == "O(n + e)"
    assert "taskOrder" in detail["input_format"] and "Any answer" in detail["output_format"]  # generated defaults
    assert detail["editorial"] is None and detail["has_editorial"] is True
    body = json.dumps(detail)
    assert "def check" not in body and "SECRET-EDITORIAL" not in body and "[[2,0],[0,1]]" not in body

    # Admins see the editorial (but still never the checker).
    admin_detail = (await async_client.get("/api/practice/problems/task-ordering", headers=auth_header(admin))).json()
    assert "SECRET-EDITORIAL" in admin_detail["editorial"]
    admin_list = (await async_client.get("/api/practice/admin/problems", headers=auth_header(admin))).json()
    full = (await async_client.get(f"/api/practice/admin/problems/{admin_list[1]['id']}", headers=auth_header(admin))).json()
    assert full["number"] == 111 and "def check" not in json.dumps(full)

    # A different valid order is accepted by the checker; solving unlocks the editorial.
    fake_sandbox.result = SandboxResult("success", _records(
        {"i": 0, "ok": True, "result": [1, 0], "ms": 1, "stdout": ""},
        {"i": 1, "ok": True, "result": [2, 0, 1], "ms": 1, "stdout": ""},
    ), "", 0, 10)
    sub = (await async_client.post("/api/practice/problems/task-ordering/submit", headers=headers, json={"language": "python", "code": "x"})).json()
    assert sub["verdict"] == "ACCEPTED", sub
    detail = (await async_client.get("/api/practice/problems/task-ordering", headers=headers)).json()
    assert "SECRET-EDITORIAL" in detail["editorial"]

    # An order that breaks a dependency is a wrong answer, and the hidden case stays hidden.
    fake_sandbox.result = SandboxResult("success", _records(
        {"i": 0, "ok": True, "result": [0, 1], "ms": 1, "stdout": ""},
        {"i": 1, "ok": True, "result": [0, 1, 2], "ms": 1, "stdout": ""},
    ), "", 0, 10)
    sub = (await async_client.post("/api/practice/problems/task-ordering/submit", headers=headers, json={"language": "java", "code": "y"})).json()
    assert sub["verdict"] == "WRONG_ANSWER" and sub["failure"]["input"] is None and sub["failure"]["expected"] is None


async def test_admin_api_cannot_set_or_enable_a_checker(async_client: AsyncClient, seed_users, db_session):
    await _add_bank_problems(db_session)
    admin = auth_header(_user(seed_users, UserRole.ADMIN))

    payload = {**PROBLEM_PAYLOAD, "slug": "sneaky", "compare_mode": "checker", "checker": "def check(*a):\n    import os; return True\n"}
    r = await async_client.post("/api/practice/admin/problems", headers=admin, json=payload)
    assert r.status_code == 422 and "question bank" in r.json()["detail"]

    payload = {**PROBLEM_PAYLOAD, "slug": "sneaky", "checker": "def check(*a): return True"}
    r = await async_client.post("/api/practice/admin/problems", headers=admin, json=payload)
    assert r.status_code == 201
    created = (await db_session.execute(
        PracticeProblem.__table__.select().where(PracticeProblem.slug == "sneaky")
    )).mappings().one()
    assert created["checker"] is None  # the field was ignored

    # Editing a bank problem keeps its checker; the payload cannot replace it.
    pid = next(p["id"] for p in (await async_client.get("/api/practice/admin/problems", headers=admin)).json() if p["slug"] == "task-ordering")
    current = (await async_client.get(f"/api/practice/admin/problems/{pid}", headers=admin)).json()
    update = {k: current[k] for k in ("slug", "number", "topic", "title", "difficulty", "tags", "statement", "constraints", "complexity",
                                      "editorial", "hints", "judge_mode", "function_spec", "compare_mode", "starter_code",
                                      "reference_solution", "time_limit_ms", "memory_limit_mb", "is_published")}
    update["test_cases"] = [{k: c[k] for k in ("input_data", "expected_output", "is_sample")} for c in current["test_cases"]]
    update["checker"] = "def check(*a): return True"
    r = await async_client.put(f"/api/practice/admin/problems/{pid}", headers=admin, json=update)
    assert r.status_code == 200, r.text
    await db_session.commit()
    kept = (await db_session.execute(
        PracticeProblem.__table__.select().where(PracticeProblem.slug == "task-ordering")
    )).mappings().one()
    assert kept["checker"] == TOPO_CHECKER


async def test_problem_numbers_are_unique(async_client: AsyncClient, seed_users, db_session):
    await _add_bank_problems(db_session)
    admin = auth_header(_user(seed_users, UserRole.ADMIN))
    r = await async_client.post("/api/practice/admin/problems", headers=admin, json={**PROBLEM_PAYLOAD, "number": 111})
    assert r.status_code == 409 and "111" in r.json()["detail"]
    r = await async_client.post("/api/practice/admin/problems", headers=admin, json={**PROBLEM_PAYLOAD, "number": 301, "topic": "Arrays"})
    assert r.status_code == 201 and r.json()["number"] == 301


async def test_submission_history_and_topic_progress(async_client: AsyncClient, seed_users, db_session, fake_sandbox):
    await _add_bank_problems(db_session)
    candidate, admin = _user(seed_users, UserRole.CANDIDATE), _user(seed_users, UserRole.ADMIN)
    headers = auth_header(candidate)

    fake_sandbox.result = SandboxResult("success", _records({"i": 0, "ok": True, "result": 7, "ms": 1, "stdout": ""}), "", 0, 10)
    await async_client.post("/api/practice/problems/lone-value/submit", headers=headers, json={"language": "python", "code": "a"})
    fake_sandbox.result = SandboxResult("success", _records({"i": 0, "ok": True, "result": 1, "ms": 1, "stdout": ""}), "", 0, 10)
    await async_client.post("/api/practice/problems/lone-value/submit", headers=headers, json={"language": "cpp", "code": "b"})
    fake_sandbox.result = SandboxResult("success", _records({"i": 0, "ok": True, "result": 0, "ms": 1, "stdout": ""}), "", 0, 10)
    await async_client.post("/api/practice/problems/pair-with-target-sum/submit", headers=headers, json={"language": "java", "code": "c"})

    history = (await async_client.get("/api/practice/submissions", headers=headers)).json()
    assert history["total"] == 3
    assert [(h["problem_number"], h["verdict"], h["language"]) for h in history["items"]] == [
        (1, "WRONG_ANSWER", "java"), (116, "ACCEPTED", "cpp"), (116, "WRONG_ANSWER", "python"),
    ]
    assert "source_code" not in history["items"][0]
    accepted = (await async_client.get("/api/practice/submissions?verdict=ACCEPTED", headers=headers)).json()
    assert accepted["total"] == 1
    page = (await async_client.get("/api/practice/submissions?limit=1&offset=1", headers=headers)).json()
    assert page["total"] == 3 and page["items"][0]["problem_number"] == 116

    stats = (await async_client.get("/api/practice/stats/me", headers=headers)).json()
    progress = {t["topic"]: (t["solved"], t["attempted"], t["total"]) for t in stats["by_topic"]}
    assert progress == {"Hashing": (0, 1, 1), "Graphs": (0, 0, 1), "Bit Manipulation": (1, 0, 1)}

    # History is per user.
    assert (await async_client.get("/api/practice/submissions", headers=auth_header(admin))).json()["total"] == 0


async def test_playground_runs_programs_with_limits(async_client: AsyncClient, seed_users, monkeypatch):
    from app.api import sandbox as sandbox_api

    calls = []

    async def execute_async(language, source_code, stdin, timeout_sec, memory_mb, **_):
        calls.append((language, stdin, timeout_sec, memory_mb))
        if "syntax" in source_code:
            return SandboxResult("compile_error", "", "main.c:1: error: expected ';'", 1, 30, "main.c:1: error: expected ';'")
        return SandboxResult("error", "partial\n", "Segmentation fault", 139, 40)

    monkeypatch.setattr(sandbox_api.sandbox_service, "execute_async", execute_async)
    headers = auth_header(_user(seed_users, UserRole.CANDIDATE))

    r = (await async_client.post("/api/sandbox/execute", headers=headers, json={"language": "c", "code": "int main(){}", "stdin": "5\n"})).json()
    assert r["status"] == "error" and r["exit_code"] == 139 and r["stdout"] == "partial\n" and "Segmentation" in r["stderr"]
    assert calls[-1] == ("c", "5\n", 5.0, 256)

    r = (await async_client.post("/api/sandbox/execute", headers=headers, json={"language": "C++", "code": "syntax"})).json()
    assert r["status"] == "compile_error" and "expected ';'" in r["compile_output"] and r["stderr"] == ""
    assert calls[-1][0] == "cpp"

    r = await async_client.post("/api/sandbox/execute", headers=headers, json={"language": "ruby", "code": "puts 1"})
    assert r.status_code == 400
    r = await async_client.post("/api/sandbox/execute", headers=headers, json={"language": "python", "code": "x" * 50_001})
    assert r.status_code == 422
    r = await async_client.post("/api/sandbox/execute", headers=headers, json={"language": "python", "code": "print(1)", "stdin": "x" * 64_001})
    assert r.status_code == 422


async def test_playground_hides_engine_internals_on_outage(async_client: AsyncClient, seed_users, monkeypatch):
    from app.api import sandbox as sandbox_api

    async def execute_async(*_a, **_k):
        return SandboxResult("system_error", "", "Execution engine error: http://piston:2000 PayloadTooLarge", -1, 5)

    monkeypatch.setattr(sandbox_api.sandbox_service, "execute_async", execute_async)
    r = (await async_client.post("/api/sandbox/execute", headers=auth_header(_user(seed_users, UserRole.CANDIDATE)),
                                 json={"language": "python", "code": "print(1)"})).json()
    assert r["status"] == "system_error" and "piston" not in r["stderr"].lower()


async def test_code_execution_is_rate_limited_without_redis(async_client: AsyncClient, seed_users, monkeypatch):
    """Redis is absent in tests, so this exercises the in-process fallback window."""
    from app.api import sandbox as sandbox_api

    async def execute_async(*_a, **_k):
        return SandboxResult("success", "1\n", "", 0, 5)

    monkeypatch.setattr(sandbox_api.sandbox_service, "execute_async", execute_async)
    headers = auth_header(_user(seed_users, UserRole.CANDIDATE))
    codes = [
        (await async_client.post("/api/sandbox/execute", headers=headers, json={"language": "python", "code": "print(1)"})).status_code
        for _ in range(31)
    ]
    assert codes[:30] == [200] * 30 and codes[30] == 429
