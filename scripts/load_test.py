"""Exam-rush load test: N students sign in and submit code at the same moment.

    .venv/Scripts/python scripts/load_test.py --students 100
    .venv/Scripts/python scripts/load_test.py --students 200 --api http://localhost:8000
    .venv/Scripts/python scripts/load_test.py --cleanup          # remove the load-test accounts

Creates development-only accounts (loadtest-N@loadtest.example.edu) directly in the database the
backend uses (backend/.env), so run it on a development or staging stack - never production.
Each student submits a correct solution to "Pair With Target Sum" through the public API; a
202 (queued) response is followed by polling until the verdict is ready, as the web app does.
"""

import argparse
import asyncio
import os
import statistics
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT / "backend")  # so backend/.env (DATABASE_URL) is used

PASSWORD = "LoadTest-Only-Pass-1"  # development-only accounts created by this script
SLUG = "pair-with-target-sum"
SOLUTION = (
    "class Solution:\n"
    "    def pairSum(self, nums, target):\n"
    "        seen = {}\n"
    "        for i, x in enumerate(nums):\n"
    "            if target - x in seen:\n"
    "                return [seen[target - x], i]\n"
    "            seen[x] = i\n"
)


def email(i: int) -> str:
    return f"loadtest-{i}@loadtest.example.edu"


async def ensure_accounts(n: int) -> None:
    from sqlalchemy import select

    from app import models  # noqa: F401
    from app.core.config import settings
    from app.core.database import async_session_maker
    from app.core.security import get_password_hash
    from app.models.user import User, UserRole

    if settings.ENVIRONMENT.lower() == "production":
        raise SystemExit("Refusing to create load-test accounts in production.")
    hashed = get_password_hash(PASSWORD)
    async with async_session_maker() as db:
        existing = set((await db.execute(select(User.email).where(User.email.like("loadtest-%@loadtest.example.edu")))).scalars())
        new = [User(email=email(i), hashed_password=hashed, full_name=f"Load Test {i}", role=UserRole.CANDIDATE, is_active=True)
               for i in range(n) if email(i) not in existing]
        db.add_all(new)
        await db.commit()
    print(f"accounts: {n} ready ({len(new)} created)")


async def cleanup() -> None:
    from sqlalchemy import delete, select

    from app import models  # noqa: F401
    from app.core.database import async_session_maker
    from app.models.practice import PracticeSubmission
    from app.models.user import User

    async with async_session_maker() as db:
        ids = list((await db.execute(select(User.id).where(User.email.like("loadtest-%@loadtest.example.edu")))).scalars())
        if ids:
            await db.execute(delete(PracticeSubmission).where(PracticeSubmission.user_id.in_(ids)))
            await db.execute(delete(User).where(User.id.in_(ids)))
            await db.commit()
    print(f"removed {len(ids)} load-test accounts and their submissions")


def pct(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    values = sorted(values)
    return values[min(len(values) - 1, int(round(p / 100 * (len(values) - 1))))]


async def student(client: httpx.AsyncClient, i: int, start: asyncio.Event, out: dict) -> None:
    """One simulated student; transport errors are recorded, not raised, so one dropped
    connection does not end the whole run."""
    try:
        await _student(client, i, start, out)
    except httpx.HTTPError as exc:
        out["errors"].append(f"{type(exc).__name__}: {exc}"[:160])


async def _student(client: httpx.AsyncClient, i: int, start: asyncio.Event, out: dict) -> None:
    t0 = time.perf_counter()
    try:
        r = await client.post("/api/auth/login", json={"email": email(i), "password": PASSWORD})
    finally:
        out["login_ms"].append((time.perf_counter() - t0) * 1000)
    out["login_codes"][r.status_code] = out["login_codes"].get(r.status_code, 0) + 1
    if r.status_code != 200:
        return
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}

    await start.wait()  # everyone submits at the same moment
    t0 = time.perf_counter()
    r = await client.post(f"/api/practice/problems/{SLUG}/submit", headers=headers,
                          json={"language": "python", "code": SOLUTION})
    out["submit_codes"][r.status_code] = out["submit_codes"].get(r.status_code, 0) + 1
    if r.status_code not in (200, 202):
        out["errors"].append(f"submit {r.status_code}: {r.text[:120]}")
        return
    body = r.json()
    while body["verdict"] == "PENDING":
        await asyncio.sleep(1.0)
        body = (await client.get(f"/api/practice/submissions/{body['id']}", headers=headers)).json()
    out["verdict_ms"].append((time.perf_counter() - t0) * 1000)
    out["verdicts"][body["verdict"]] = out["verdicts"].get(body["verdict"], 0) + 1


async def run(api: str, n: int) -> None:
    await ensure_accounts(n)
    out = {"login_ms": [], "login_codes": {}, "submit_codes": {}, "verdict_ms": [], "verdicts": {}, "errors": []}
    start = asyncio.Event()
    limits = httpx.Limits(max_connections=n + 10, max_keepalive_connections=n + 10)
    async with httpx.AsyncClient(base_url=api, timeout=httpx.Timeout(120.0), limits=limits) as client:
        tasks = [asyncio.create_task(student(client, i, start, out)) for i in range(n)]
        while len(out["login_ms"]) < n:  # wait until every student has signed in
            await asyncio.sleep(0.1)
        t0 = time.perf_counter()
        start.set()
        await asyncio.gather(*tasks)
        wall = time.perf_counter() - t0

    print(f"\n=== {n} students ===")
    login_ms = out["login_ms"]
    print(f"sign-in      codes {out['login_codes']}  p50 {pct(login_ms, 50):.0f} ms  "
          f"p95 {pct(login_ms, 95):.0f} ms  max {max(login_ms, default=0):.0f} ms")
    print(f"submit       codes {out['submit_codes']}  (202 = queued, then polled)")
    print(f"verdicts     {out['verdicts']}")
    if out["verdict_ms"]:
        print(f"to verdict   p50 {pct(out['verdict_ms'], 50) / 1000:.1f} s  p95 {pct(out['verdict_ms'], 95) / 1000:.1f} s  "
              f"max {max(out['verdict_ms']) / 1000:.1f} s  mean {statistics.mean(out['verdict_ms']) / 1000:.1f} s")
    print(f"throughput   {len(out['verdict_ms']) / wall:.1f} verdicts/s over {wall:.1f} s")
    print(f"errors       {len(out['errors'])}")
    for e in out["errors"][:5]:
        print("  ", e)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--students", type=int, default=50)
    parser.add_argument("--api", default=os.getenv("API_URL", "http://localhost:8000"))
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()
    asyncio.run(cleanup() if args.cleanup else run(args.api, args.students))


if __name__ == "__main__":
    main()
