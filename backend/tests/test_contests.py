"""Timed contests: visibility before the start, registration, the submission window, scoring,
penalties, editorial hiding and admin rules. The engine is faked here."""

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select, update

from app.models.contest import Contest
from app.models.practice import PracticeProblem, PracticeSubmission, Verdict
from app.models.user import UserRole
from app.services.sandbox_service import SandboxResult
from tests.test_exam_engine import auth_header
from tests.test_practice import PROBLEM_PAYLOAD, _records, _user, fake_sandbox  # noqa: F401  (fixture)


@pytest_asyncio.fixture
async def db_session():
    from tests.conftest import test_async_session_maker

    async with test_async_session_maker() as session:
        yield session


ACCEPT = SandboxResult("success", _records(
    {"i": 0, "ok": True, "result": 6, "ms": 1, "stdout": ""},
    {"i": 1, "ok": True, "result": 99, "ms": 1, "stdout": ""},
), "", 0, 10)
WRONG = SandboxResult("success", _records(
    {"i": 0, "ok": True, "result": 6, "ms": 1, "stdout": ""},
    {"i": 1, "ok": True, "result": 0, "ms": 1, "stdout": ""},
), "", 0, 10)
COMPILE_ERROR = SandboxResult("compile_error", "", "main.py: syntax error", 1, 10, "main.py: syntax error")


async def _problems(client: AsyncClient, admin) -> list[str]:
    """Two problems: one published in practice, one contest-only. Returns their ids."""
    ids = []
    for slug, published in (("add-up", True), ("add-up-again", False)):
        body = {**PROBLEM_PAYLOAD, "slug": slug, "title": slug.replace("-", " ").title(), "is_published": published,
                "editorial": "SECRET-EDITORIAL"}
        r = await client.post("/api/practice/admin/problems", headers=auth_header(admin), json=body)
        assert r.status_code == 201, r.text
        ids.append(r.json()["id"])
    return ids


def _contest_body(problem_ids: list[str], starts_at: datetime, minutes: int = 90, **extra) -> dict:
    return {
        "slug": "weekly-1", "title": "Weekly Contest 1", "description": "Two problems.",
        "starts_at": starts_at.isoformat(), "duration_minutes": minutes, "is_published": True,
        "problems": [{"problem_id": problem_ids[0], "points": 100}, {"problem_id": problem_ids[1], "points": 300}],
        **extra,
    }


async def _create(client: AsyncClient, admin, body: dict) -> dict:
    r = await client.post("/api/admin/contests", headers=auth_header(admin), json=body)
    assert r.status_code == 201, r.text
    return r.json()


async def test_upcoming_contest_hides_problems_everywhere(async_client: AsyncClient, seed_users):
    admin, candidate = _user(seed_users, UserRole.ADMIN), _user(seed_users, UserRole.CANDIDATE)
    ids = await _problems(async_client, admin)
    await _create(async_client, admin, _contest_body(ids, datetime.now(timezone.utc) + timedelta(hours=1)))
    headers = auth_header(candidate)

    listing = (await async_client.get("/api/contests", headers=headers)).json()["items"]
    assert [(c["slug"], c["phase"], c["registered"]) for c in listing] == [("weekly-1", "upcoming", False)]

    detail = (await async_client.get("/api/contests/weekly-1", headers=headers)).json()
    assert detail["problems"] == [] and detail["problem_count"] == 2
    assert (await async_client.get("/api/contests/weekly-1/problems/add-up", headers=headers)).status_code == 403
    r = await async_client.post("/api/contests/weekly-1/problems/add-up/run", headers=headers, json={"language": "python", "code": "x"})
    assert r.status_code == 403

    # The published problem is locked out of practice until the contest ends.
    practice = (await async_client.get("/api/practice/problems", headers=headers)).json()["items"]
    assert practice == []
    assert (await async_client.get("/api/practice/problems/add-up", headers=headers)).status_code == 404
    r = await async_client.post("/api/practice/problems/add-up/submit", headers=headers, json={"language": "python", "code": "x"})
    assert r.status_code == 404

    # Registration opens before the start; submissions do not.
    r = await async_client.post("/api/contests/weekly-1/register", headers=headers)
    assert r.status_code == 200 and r.json()["registered"] is True and r.json()["participants"] == 1
    r = await async_client.post("/api/contests/weekly-1/problems/add-up/submit", headers=headers, json={"language": "python", "code": "x"})
    assert r.status_code == 403 and "not started" in r.json()["detail"]

    # Admins see everything, including the editorial.
    assert len((await async_client.get("/api/contests/weekly-1", headers=auth_header(admin))).json()["problems"]) == 2


async def test_unpublished_contest_is_invisible_to_students(async_client: AsyncClient, seed_users):
    admin, candidate = _user(seed_users, UserRole.ADMIN), _user(seed_users, UserRole.CANDIDATE)
    ids = await _problems(async_client, admin)
    await _create(async_client, admin, _contest_body(ids, datetime.now(timezone.utc) - timedelta(minutes=5), is_published=False))
    headers = auth_header(candidate)
    assert (await async_client.get("/api/contests", headers=headers)).json()["items"] == []
    assert (await async_client.get("/api/contests/weekly-1", headers=headers)).status_code == 404
    assert (await async_client.post("/api/contests/weekly-1/register", headers=headers)).status_code == 404
    # An unpublished contest does not lock its problems out of practice.
    assert (await async_client.get("/api/practice/problems/add-up", headers=headers)).status_code == 200


async def test_running_contest_submit_window_and_scoring(async_client: AsyncClient, seed_users, fake_sandbox):
    admin, candidate = _user(seed_users, UserRole.ADMIN), _user(seed_users, UserRole.CANDIDATE)
    ids = await _problems(async_client, admin)
    await _create(async_client, admin, _contest_body(ids, datetime.now(timezone.utc) - timedelta(minutes=10)))
    headers = auth_header(candidate)
    submit = "/api/contests/weekly-1/problems/add-up-again/submit"

    # Contest-only problem: readable inside the contest, without the editorial.
    problem = (await async_client.get("/api/contests/weekly-1/problems/add-up-again", headers=headers)).json()
    assert problem["title"] == "Add Up Again" and problem["editorial"] is None and problem["has_editorial"] is True
    assert "99" not in str(problem["examples"])  # hidden case stays hidden

    r = await async_client.post(submit, headers=headers, json={"language": "python", "code": "x"})
    assert r.status_code == 403 and "Register" in r.json()["detail"]
    await async_client.post("/api/contests/weekly-1/register", headers=headers)

    fake_sandbox.result = COMPILE_ERROR
    assert (await async_client.post(submit, headers=headers, json={"language": "python", "code": "x"})).json()["verdict"] == "COMPILE_ERROR"
    fake_sandbox.result = WRONG
    assert (await async_client.post(submit, headers=headers, json={"language": "python", "code": "x"})).json()["verdict"] == "WRONG_ANSWER"
    fake_sandbox.result = ACCEPT
    assert (await async_client.post(submit, headers=headers, json={"language": "python", "code": "y"})).json()["verdict"] == "ACCEPTED"

    board = (await async_client.get("/api/contests/weekly-1/leaderboard", headers=headers)).json()
    assert board["labels"] == ["A", "B"] and board["phase"] == "running"
    row = board["rows"][0]
    assert (row["rank"], row["score"], row["solved"], row["is_me"]) == (1, 300, 1, True)
    b = row["problems"][1]
    assert b["solved"] is True and b["rejected"] == 1  # the compile error is not penalised
    assert row["penalty_minutes"] == b["solved_at_minutes"] + 5 and 9 <= b["solved_at_minutes"] <= 11

    detail = (await async_client.get("/api/contests/weekly-1", headers=headers)).json()
    assert [(p["label"], p["status"], p["solved_by"]) for p in detail["problems"]] == [("A", "todo", 0), ("B", "solved", 1)]
    per_problem = (await async_client.get("/api/contests/weekly-1/problems/add-up-again/submissions", headers=headers)).json()
    assert [s["verdict"] for s in per_problem] == ["ACCEPTED", "WRONG_ANSWER", "COMPILE_ERROR"]
    assert (await async_client.get("/api/contests/weekly-1/problems/add-up/submissions", headers=headers)).json() == []
    mine = (await async_client.get("/api/contests/weekly-1/submissions", headers=headers)).json()
    assert [(s["label"], s["verdict"]) for s in mine] == [("B", "ACCEPTED"), ("B", "WRONG_ANSWER"), ("B", "COMPILE_ERROR")]
    # Editorial stays hidden while the contest runs, even after solving.
    problem = (await async_client.get("/api/contests/weekly-1/problems/add-up-again", headers=headers)).json()
    assert problem["status"] == "solved" and problem["editorial"] is None


async def test_ended_contest_closes_submissions_and_reveals_editorial(async_client: AsyncClient, seed_users, fake_sandbox, db_session):
    admin, candidate = _user(seed_users, UserRole.ADMIN), _user(seed_users, UserRole.CANDIDATE)
    ids = await _problems(async_client, admin)
    await _create(async_client, admin, _contest_body(ids, datetime.now(timezone.utc) - timedelta(minutes=30)))
    headers = auth_header(candidate)
    await async_client.post("/api/contests/weekly-1/register", headers=headers)
    fake_sandbox.result = ACCEPT
    r = await async_client.post("/api/contests/weekly-1/problems/add-up/submit", headers=headers, json={"language": "python", "code": "y"})
    assert r.json()["verdict"] == "ACCEPTED"

    # Move the contest into the past.
    now = datetime.now(timezone.utc)
    await db_session.execute(update(Contest).values(starts_at=now - timedelta(hours=2), ends_at=now - timedelta(minutes=1)))
    await db_session.execute(update(PracticeSubmission).values(created_at=now - timedelta(minutes=90)))
    await db_session.commit()

    r = await async_client.post("/api/contests/weekly-1/problems/add-up/submit", headers=headers, json={"language": "python", "code": "y"})
    assert r.status_code == 403 and "ended" in r.json()["detail"]
    assert (await async_client.post("/api/contests/weekly-1/register", headers=headers)).status_code == 409
    problem = (await async_client.get("/api/contests/weekly-1/problems/add-up", headers=headers)).json()
    assert problem["editorial"] == "SECRET-EDITORIAL"
    unsolved = (await async_client.get("/api/contests/weekly-1/problems/add-up-again", headers=headers)).json()
    assert unsolved["editorial"] is None  # still earned by solving
    # Practice gets the published problem back once the contest is over; the contest-only one stays out.
    practice = (await async_client.get("/api/practice/problems", headers=headers)).json()["items"]
    assert [p["slug"] for p in practice] == ["add-up"] and practice[0]["status"] == "solved"
    board = (await async_client.get("/api/contests/weekly-1/leaderboard", headers=headers)).json()
    assert board["phase"] == "ended" and board["rows"][0]["score"] == 100 and board["rows"][0]["penalty_minutes"] == 30


async def test_ranking_uses_score_then_penalty_then_last_accepted(async_client: AsyncClient, seed_users, db_session):
    admin = _user(seed_users, UserRole.ADMIN)
    candidate, proctor, reviewer = (_user(seed_users, r) for r in (UserRole.CANDIDATE, UserRole.PROCTOR, UserRole.REVIEWER))
    ids = await _problems(async_client, admin)
    starts = datetime.now(timezone.utc) - timedelta(hours=1)
    await _create(async_client, admin, _contest_body(ids, starts, minutes=120))
    for user in (candidate, proctor, reviewer, admin):
        await async_client.post("/api/contests/weekly-1/register", headers=auth_header(user))
    contest_id = (await db_session.execute(select(Contest.id))).scalar_one()
    a, b = (await db_session.execute(select(PracticeProblem.id).order_by(PracticeProblem.slug))).scalars().all()

    def sub(user, problem, verdict, minute):
        return PracticeSubmission(problem_id=problem, user_id=user.id, language="python", source_code="x", verdict=verdict,
                                  passed_count=0, total_count=2, contest_id=contest_id, created_at=starts + timedelta(minutes=minute))

    db_session.add_all([
        # candidate: A at 10 + B at 40 -> 400 points, penalty 50
        sub(candidate, a, Verdict.ACCEPTED, 10), sub(candidate, b, Verdict.ACCEPTED, 40),
        # proctor: B at 20 after two rejections -> 300 points, penalty 30
        sub(proctor, b, Verdict.WRONG_ANSWER, 5), sub(proctor, b, Verdict.TIME_LIMIT_EXCEEDED, 8), sub(proctor, b, Verdict.ACCEPTED, 20),
        # reviewer: B at 30 -> 300 points, penalty 30, but later last accept than proctor... equal penalty, proctor first
        sub(reviewer, b, Verdict.ACCEPTED, 30),
        # admin: only rejections (and a later, ignored, wrong answer after nothing) -> 0 points
        sub(admin, a, Verdict.WRONG_ANSWER, 3), sub(admin, a, Verdict.SYSTEM_ERROR, 4),
        # a practice submission (no contest_id) never counts
        PracticeSubmission(problem_id=a, user_id=reviewer.id, language="python", source_code="x", verdict=Verdict.ACCEPTED,
                           passed_count=2, total_count=2, created_at=starts + timedelta(minutes=1)),
    ])
    await db_session.commit()

    board = (await async_client.get("/api/contests/weekly-1/leaderboard", headers=auth_header(candidate))).json()
    rows = [(r["rank"], r["user_id"], r["score"], r["penalty_minutes"]) for r in board["rows"]]
    assert rows == [
        (1, str(candidate.id), 400, 50),
        (2, str(proctor.id), 300, 30),
        (3, str(reviewer.id), 300, 30),
        (4, str(admin.id), 0, 0),
    ]
    admin_row = board["rows"][3]["problems"][0]
    assert admin_row == {"label": "A", "solved": False, "rejected": 1, "solved_at_minutes": None}


async def test_admin_rules(async_client: AsyncClient, seed_users):
    admin, candidate = _user(seed_users, UserRole.ADMIN), _user(seed_users, UserRole.CANDIDATE)
    ids = await _problems(async_client, admin)
    body = _contest_body(ids, datetime.now(timezone.utc) + timedelta(days=1))

    assert (await async_client.post("/api/admin/contests", headers=auth_header(candidate), json=body)).status_code == 403
    assert (await async_client.post("/api/admin/contests", headers=auth_header(admin),
                                    json={**body, "problems": [body["problems"][0]] * 2})).status_code == 422
    unknown = {**body, "problems": [{"problem_id": "00000000-0000-0000-0000-000000000001", "points": 5}]}
    assert (await async_client.post("/api/admin/contests", headers=auth_header(admin), json=unknown)).status_code == 422

    created = await _create(async_client, admin, body)
    assert [p["label"] for p in created["problems"]] == ["A", "B"] and created["problems"][1]["is_published"] is False
    assert (await async_client.post("/api/admin/contests", headers=auth_header(admin), json=body)).status_code == 409

    # Before the start, everything can change (including reordering the same problems).
    swapped = {**body, "problems": body["problems"][::-1], "title": "Renamed"}
    r = await async_client.put(f"/api/admin/contests/{created['id']}", headers=auth_header(admin), json=swapped)
    assert r.status_code == 200, r.text
    assert [p["slug"] for p in r.json()["problems"]] == ["add-up-again", "add-up"]

    # Once started, only cosmetic fields can change.
    started = {**swapped, "starts_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()}
    r = await async_client.put(f"/api/admin/contests/{created['id']}", headers=auth_header(admin), json=started)
    assert r.status_code == 200  # moving the start is allowed while it is still upcoming
    r = await async_client.put(f"/api/admin/contests/{created['id']}", headers=auth_header(admin),
                               json={**started, "problems": [{**p, "points": 1} for p in started["problems"]]})
    assert r.status_code == 409
    r = await async_client.put(f"/api/admin/contests/{created['id']}", headers=auth_header(admin),
                               json={**started, "description": "Good luck!"})
    assert r.status_code == 200 and r.json()["description"] == "Good luck!"

    assert (await async_client.delete(f"/api/admin/contests/{created['id']}", headers=auth_header(admin))).status_code == 204
    assert (await async_client.get("/api/admin/contests", headers=auth_header(admin))).json() == []


def test_sqlite_dev_database_gains_new_columns(tmp_path):
    """Older local SQLite databases get columns that newer models add (create_all never alters)."""
    import sqlalchemy as sa

    from app.core.database import Base
    from app.main import _sqlite_add_missing_columns

    engine = sa.create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    current = Base.metadata.tables["practice_submissions"]
    old = sa.MetaData()
    sa.Table("practice_submissions", old, *[
        sa.Column(c.name, c.type, primary_key=c.primary_key, nullable=c.nullable)
        for c in current.columns if c.name not in ("contest_id", "judge_attempts")
    ])
    with engine.begin() as conn:
        old.create_all(conn)
    with engine.begin() as conn:
        added = _sqlite_add_missing_columns(conn, Base.metadata)
        assert sorted(added) == ["practice_submissions.contest_id", "practice_submissions.judge_attempts"]
        assert _sqlite_add_missing_columns(conn, Base.metadata) == []
        columns = {c["name"]: c for c in sa.inspect(conn).get_columns("practice_submissions")}
        assert columns["contest_id"]["nullable"] and columns["judge_attempts"]["default"] == "'0'"

    # A unique constraint added to a model later becomes a unique index (when the data allows it).
    sessions = Base.metadata.tables["exam_sessions"]
    old_sessions = sa.MetaData()
    sa.Table("exam_sessions", old_sessions, *[sa.Column(c.name, c.type, primary_key=c.primary_key, nullable=True) for c in sessions.columns])
    with engine.begin() as conn:
        old_sessions.create_all(conn)
        added = _sqlite_add_missing_columns(conn, Base.metadata)
        assert "exam_sessions:uq_exam_session_candidate" in added
        conn.exec_driver_sql("INSERT INTO exam_sessions (id, exam_id, candidate_id) VALUES ('a', 'e', 'c')")
        with pytest.raises(sa.exc.IntegrityError):
            conn.exec_driver_sql("INSERT INTO exam_sessions (id, exam_id, candidate_id) VALUES ('b', 'e', 'c')")
    engine.dispose()
