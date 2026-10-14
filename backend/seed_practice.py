"""Seed the practice problem bank (idempotent: problems are upserted by slug).

    cd backend && python seed_practice.py

Expected outputs are not hand-written: each problem's Python reference
solution is executed here to compute them, so test data and reference always
agree. Statements are original to ExamSentinel.
"""

import asyncio
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app import models  # noqa: F401  (registers all models)
from app.core.database import Base, async_session_maker, engine
from app.models.practice import JudgeMode, PracticeProblem, PracticeTestCase
from practice_bank import PROBLEMS


# ---------------------------------------------------------------------------

def run_reference(code: str, method: str, args: tuple) -> Any:
    ns: dict = {}
    exec(code, ns)  # trusted, repo-authored reference solutions only
    return getattr(ns["Solution"](), method)(*[json.loads(json.dumps(a)) for a in args])


def run_stdio_reference(code: str, stdin: str) -> str:
    import contextlib
    import io
    import sys

    out = io.StringIO()
    old_stdin = sys.stdin
    sys.stdin = io.StringIO(stdin)
    try:
        with contextlib.redirect_stdout(out):
            exec(code, {"__name__": "__main__"})
    finally:
        sys.stdin = old_stdin
    return out.getvalue()


def run_sql_reference(schema: str, inserts: str, query: str) -> list[list]:
    import sqlite3

    db = sqlite3.connect(":memory:")
    try:
        db.executescript(schema + "\n" + inserts)
        return [list(row) for row in db.execute(query).fetchall()]
    finally:
        db.close()


def build_cases(p: dict) -> list[PracticeTestCase]:
    cases = []
    if p.get("judge_mode") == JudgeMode.SQL:
        compact = lambda rows: json.dumps(rows, separators=(",", ":"))  # noqa: E731
        for inserts, expl in p["sql_samples"]:
            cases.append((inserts.strip(), compact(run_sql_reference(p["sql_schema"], inserts, p["reference"])), True, expl))
        for inserts in p["sql_hidden"]:
            cases.append((inserts.strip(), compact(run_sql_reference(p["sql_schema"], inserts, p["reference"])), False, None))
    elif p.get("judge_mode") == JudgeMode.STDIO:
        for stdin, expl in p["stdio_samples"]:
            cases.append((stdin, run_stdio_reference(p["reference"], stdin).strip(), True, expl))
        for stdin in p["stdio_hidden"]:
            cases.append((stdin, run_stdio_reference(p["reference"], stdin).strip(), False, None))
    else:
        method = p["spec"]["name"]
        to_input = lambda args: "\n".join(json.dumps(a, separators=(",", ":")) for a in args)  # noqa: E731
        for args, expl in p["samples"]:
            cases.append((to_input(args), json.dumps(run_reference(p["reference"], method, args), separators=(",", ":")), True, expl))
        for args in p["hidden"]:
            args = args if isinstance(args, tuple) else (args,)
            cases.append((to_input(args), json.dumps(run_reference(p["reference"], method, args), separators=(",", ":")), False, None))
    return [
        PracticeTestCase(input_data=i, expected_output=o, is_sample=s, explanation=e, order_index=n)
        for n, (i, o, s, e) in enumerate(cases)
    ]


async def seed() -> None:
    async with engine.begin() as conn:
        if engine.url.get_backend_name() == "sqlite":
            await conn.run_sync(Base.metadata.create_all)
    async with async_session_maker() as db:
        for p in PROBLEMS:
            existing = (await db.execute(
                select(PracticeProblem).options(selectinload(PracticeProblem.test_cases)).where(PracticeProblem.slug == p["slug"])
            )).scalar_one_or_none()
            problem_row = existing or PracticeProblem(slug=p["slug"])
            problem_row.title = p["title"]
            problem_row.difficulty = p["difficulty"]
            problem_row.tags = p["tags"]
            problem_row.statement = p["statement"]
            problem_row.constraints = p.get("constraints")
            problem_row.hints = p.get("hints", [])
            problem_row.judge_mode = p.get("judge_mode", JudgeMode.FUNCTION)
            problem_row.function_spec = p.get("spec")
            problem_row.sql_schema = p.get("sql_schema")
            problem_row.compare_mode = p.get("compare", "exact")
            problem_row.starter_code = p.get("starter_code", {})
            ref_language = "sql" if p.get("judge_mode") == JudgeMode.SQL else "python"
            problem_row.reference_solution = {"language": ref_language, "code": p["reference"].strip() + "\n"}
            problem_row.time_limit_ms = p.get("time_limit_ms", 2000)
            problem_row.memory_limit_mb = 256
            problem_row.is_published = True
            problem_row.test_cases = build_cases(p)
            if existing is None:
                db.add(problem_row)
            print(f"{'updated' if existing else 'created'}: {p['slug']} ({len(problem_row.test_cases)} tests)")
        await db.commit()
    print(f"Seeded {len(PROBLEMS)} practice problems.")


if __name__ == "__main__":
    asyncio.run(seed())
