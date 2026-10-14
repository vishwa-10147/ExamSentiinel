"""End-to-end smoke test of the full exam lifecycle across every role.

Runs against a live backend (default http://localhost:8000) seeded with
``backend/seed_admin.py``. Uses the same request payloads the Next.js UI sends.

    python scripts/e2e_roles_smoke.py [--base-url URL]

Exit code 0 when every step passes.
"""

import argparse
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

import httpx

PASSWORD = os.environ.get("E2E_PASSWORD", "DemoPass123!")  # seed_admin.py demo value
RESULTS: list[tuple[str, bool, str]] = []


def step(name: str, ok: bool, detail: str = "") -> bool:
    RESULTS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))
    return ok


def login(client: httpx.Client, email: str) -> dict:
    r = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def check(name: str, r: httpx.Response, expect: int | tuple = (200, 201)) -> dict | list | None:
    expect = expect if isinstance(expect, tuple) else (expect,)
    ok = r.status_code in expect
    step(name, ok, "" if ok else f"HTTP {r.status_code}: {r.text[:300]}")
    try:
        return r.json()
    except ValueError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.environ.get("E2E_BASE_URL", "http://localhost:8000"))
    args = parser.parse_args()

    with httpx.Client(base_url=args.base_url, timeout=60) as c:
        admin = login(c, "admin@sentinel.edu")
        proctor = login(c, "proctor@sentinel.edu")
        reviewer = login(c, "reviewer@sentinel.edu")
        candidate = login(c, "candidate@sentinel.edu")
        step("login all four roles", True)

        me = check("candidate /auth/me", c.get("/api/auth/me", headers=candidate))
        candidate_id = me["id"]

        # ---- RBAC: candidates must not reach staff endpoints -------------
        check("RBAC: candidate blocked from /users", c.get("/api/users", headers=candidate), (401, 403))
        check("RBAC: candidate blocked from review queue", c.get("/api/proctoring/review-queue", headers=candidate), (401, 403))
        check("RBAC: reviewer blocked from creating exams",
              c.post("/api/exams", headers=reviewer, json={"title": "x", "start_window": "2026-01-01T00:00:00Z", "end_window": "2026-01-02T00:00:00Z"}),
              (401, 403))

        # ---- Admin builds and publishes an exam --------------------------
        now = datetime.now(timezone.utc)
        exam = check("admin creates exam", c.post("/api/exams", headers=admin, json={
            "title": f"E2E Smoke {uuid.uuid4().hex[:6]}",
            "description": "Automated lifecycle check",
            "duration_minutes": 30,
            "start_window": (now - timedelta(minutes=5)).isoformat(),
            "end_window": (now + timedelta(hours=2)).isoformat(),
        }))
        exam_id = exam["id"]

        questions = [
            {"type": "MCQ_SINGLE", "title": "2 + 2 = ?", "content_rich_text": "2 + 2 = ?", "points": 2, "difficulty": "easy",
             "options": [{"id": "3", "text": "3"}, {"id": "4", "text": "4"}], "correct_answer": "4"},
            {"type": "MCQ_MULTI", "title": "Prime numbers", "content_rich_text": "Pick the primes", "points": 2, "difficulty": "easy",
             "options": [{"id": "2", "text": "2"}, {"id": "4", "text": "4"}, {"id": "5", "text": "5"}], "correct_answer": ["2", "5"]},
            {"type": "SHORT_ANSWER", "title": "Capital of France", "content_rich_text": "Capital of France?", "points": 1,
             "difficulty": "easy", "options": {}, "correct_answer": "Paris"},
        ]
        qids = []
        for i, q in enumerate(questions):
            qr = check(f"admin creates {q['type']} question", c.post("/api/questions", headers=admin, json=q))
            check(f"admin assigns {q['type']} to exam",
                  c.post(f"/api/exams/{exam_id}/questions", headers=admin, json={"question_id": qr["id"], "order_index": i}))
            qids.append(qr["id"])

        check("admin enrolls candidate", c.post(f"/api/exams/{exam_id}/enroll", headers=admin, json={"candidate_ids": [candidate_id]}))
        check("admin publishes exam", c.put(f"/api/exams/{exam_id}", headers=admin, json={"status": "PUBLISHED"}))

        # ---- Candidate takes the exam ------------------------------------
        listed = check("candidate lists exams", c.get("/api/exams", headers=candidate))
        items = listed if isinstance(listed, list) else (listed or {}).get("items", [])
        step("candidate sees enrolled exam", any(e.get("id") == exam_id for e in items))

        sess = check("candidate starts session", c.post("/api/exam/sessions/start", headers=candidate,
                                                         json={"exam_id": exam_id, "device_fingerprint": "e2e"}))
        sid = sess["session_id"]
        check("candidate loads session state", c.get(f"/api/exam/sessions/{sid}", headers=candidate))

        answers = [{"selected_option_id": "4"}, {"selected_option_ids": ["2", "5"]}, {"text": "Paris"}]
        for seq, (qid, data) in enumerate(zip(qids, answers), start=1):
            check(f"candidate saves answer {seq}", c.post(f"/api/exam/sessions/{sid}/answers", headers=candidate,
                                                          json={"question_id": qid, "response_data": data, "sequence_id": seq}))

        # Browser + webcam integrity signals, as the exam page and FaceTracker send them
        for et, cat, sev in [("TAB_BLUR", "BROWSER", "MEDIUM"), ("FULLSCREEN_EXIT", "BROWSER", "HIGH"),
                             ("PASTE_ATTEMPT", "BROWSER", "MEDIUM"), ("PHONE_DETECTED", "WEBCAM", "HIGH"),
                             ("MULTIPLE_FACES", "WEBCAM", "HIGH")]:
            check(f"telemetry {et}", c.post("/api/telemetry/events", headers=candidate, json={
                "session_id": sid, "event_type": et, "category": cat, "severity": sev,
                "details": {"source": "e2e"}, "client_timestamp": datetime.now(timezone.utc).isoformat()}))

        risk = check("risk score computed", c.get(f"/api/proctoring/risk/{sid}", headers=proctor))
        if risk:
            step("risk escalated to >= MEDIUM", risk.get("risk_level") in ("MEDIUM", "HIGH", "CRITICAL"),
                 f"score={risk.get('current_risk_score')} level={risk.get('risk_level')}")

        # ---- Proctor live view ------------------------------------------
        active = check("proctor sees active sessions", c.get("/api/dashboard/active-sessions?limit=50&sort_by=risk_score", headers=proctor))
        check("proctor reads event timeline", c.get(f"/api/proctoring/events/{sid}?page_size=50", headers=proctor))
        check("proctor issues live warning", c.post(f"/api/proctoring/sessions/{sid}/warning", headers=proctor,
                                                    json={"message": "Please keep your eyes on the screen."}))

        # 5 security violations: the 4th must auto-submit the session.
        state = check("candidate session state after violations", c.get(f"/api/exam/sessions/{sid}", headers=candidate))
        step("4+ violations auto-submitted the session", (state or {}).get("status") == "SUBMITTED", str((state or {}).get("status")))
        check("manual submit rejected after auto-submit", c.post(f"/api/exam/sessions/{sid}/submit", headers=candidate, json={"confirm": True}), 400)

        # ---- Reviewer resolves the integrity case ------------------------
        queue = check("reviewer loads review queue", c.get("/api/proctoring/review-queue", headers=reviewer))
        step("session appears in review queue", any(i["session_id"] == sid for i in (queue or [])), f"sid={sid} queue_ids={[i['session_id'] for i in (queue or [])][:3]}")
        check("reviewer flags violation", c.post(f"/api/proctoring/sessions/{sid}/flag-violation", headers=reviewer,
                                                 json={"reason": "Phone visible in frame", "notes": "Phone visible in frame"}))
        check("reviewer cannot resolve twice", c.post(f"/api/proctoring/sessions/{sid}/approve", headers=reviewer, json={}), 409)
        check("reviews API lists cases", c.get("/api/reviews", headers=reviewer))

        # ---- Admin publishes results; candidate views them --------------
        sessions = check("admin views exam sessions", c.get(f"/api/results/admin/exam/{exam_id}/sessions", headers=admin))
        rows = sessions if isinstance(sessions, list) else (sessions or {}).get("items", [])
        row = next((r for r in rows if str(r.get("session_id", r.get("id"))) == sid), {})
        step("auto-grading scored all objective answers (5/5)", float(row.get("score") or 0) == 5.0,
             str({k: row.get(k) for k in ("score", "integrity_score", "status")}))
        check("admin publishes results", c.post(f"/api/results/publish/{exam_id}", headers=admin))
        check("candidate result history", c.get("/api/results/history", headers=candidate))
        check("candidate detailed result", c.get(f"/api/reports/my-results/detailed/{sid}", headers=candidate))
        check("candidate leaderboard", c.get(f"/api/results/exam/{exam_id}/leaderboard", headers=candidate))
        check("admin dashboard stats", c.get("/api/dashboard/stats", headers=admin))
        check("admin analytics overview", c.get("/api/analytics/overview", headers=admin))
        check("admin audit log", c.get("/api/users/audit", headers=admin))

        # ---- Coding exam question graded on the code runner -------------
        coding_q = check("admin creates CODING question", c.post("/api/questions", headers=admin, json={
            "type": "CODING", "title": "Double it", "content_rich_text": "Read n and print 2n.", "points": 4,
            "difficulty": "easy", "options": {"allowed_languages": ["python"]},
            "correct_answer": {"test_cases": [{"input": "3\n", "output": "6"}, {"input": "-5\n", "output": "-10"}]},
        }))
        coding_exam = check("admin creates coding exam", c.post("/api/exams", headers=admin, json={
            "title": f"E2E Coding {uuid.uuid4().hex[:6]}", "duration_minutes": 30,
            "start_window": (now - timedelta(minutes=5)).isoformat(), "end_window": (now + timedelta(hours=2)).isoformat(),
        }))
        cx = coding_exam["id"]
        check("assign coding question", c.post(f"/api/exams/{cx}/questions", headers=admin, json={"question_id": coding_q["id"], "order_index": 0}))
        check("enroll for coding exam", c.post(f"/api/exams/{cx}/enroll", headers=admin, json={"candidate_ids": [candidate_id]}))
        check("publish coding exam", c.put(f"/api/exams/{cx}", headers=admin, json={"status": "PUBLISHED"}))
        csess = check("start coding exam", c.post("/api/exam/sessions/start", headers=candidate, json={"exam_id": cx}))
        csid = csess["session_id"]
        check("save code answer", c.post(f"/api/exam/sessions/{csid}/answers", headers=candidate, json={
            "question_id": coding_q["id"], "response_data": {"text": "print(2 * int(input()))", "language": "python"}, "sequence_id": 1}))
        # Server-side AI on a real photo with two people in frame (ships with ultralytics).
        try:
            import pathlib
            import ultralytics
            photo = (pathlib.Path(ultralytics.__file__).parent / "assets" / "zidane.jpg").read_bytes()
        except (ImportError, OSError):
            photo = None
        if photo:
            ai = check("webcam frame analysed by YOLO", c.post(
                f"/api/proctoring/sessions/{csid}/webcam/analyze", headers=candidate,
                files={"frame": ("frame.jpg", photo, "image/jpeg")}))
            step("AI flags a second person in frame", any(s["event_type"] == "MULTIPLE_FACES" for s in (ai or {}).get("signals", [])),
                 str([(s["event_type"], s["details"].get("people_found")) for s in (ai or {}).get("signals", [])]))
        else:
            step("webcam AI check skipped (requirements-ai.txt not installed)", True)
        check("submit coding exam", c.post(f"/api/exam/sessions/{csid}/submit", headers=candidate, json={"confirm": True}))
        crows = check("admin views coding exam sessions", c.get(f"/api/results/admin/exam/{cx}/sessions", headers=admin))
        crow = next((r for r in (crows or []) if str(r.get("id")) == csid), {})
        step("coding answer auto-graded on the code runner (4/4)", float(crow.get("score") or 0) == 4.0, str(crow.get("score")))

        # ---- Practice platform -------------------------------------------
        problems = check("student lists practice problems", c.get("/api/practice/problems", headers=candidate))
        step("practice problem bank is seeded", (problems or {}).get("total", 0) >= 20, str((problems or {}).get("total")))
        good = ("class Solution:\n    def isBalanced(self, s):\n        pairs = {')': '(', ']': '[', '}': '{'}\n        st = []\n"
                "        for ch in s:\n            if ch in pairs:\n                if not st or st.pop() != pairs[ch]:\n                    return False\n"
                "            else:\n                st.append(ch)\n        return not st\n")
        run = check("student runs sample tests", c.post("/api/practice/problems/balanced-brackets/run", headers=candidate,
                                                      json={"language": "python", "code": good, "custom_input": '"(("'}))
        step("run passes samples + custom input", (run or {}).get("verdict") == "ACCEPTED", str((run or {}).get("verdict")))
        sub = check("student submits correct solution", c.post("/api/practice/problems/balanced-brackets/submit", headers=candidate,
                                                             json={"language": "python", "code": good}))
        step("submission accepted on all tests", (sub or {}).get("verdict") == "ACCEPTED",
             f"{(sub or {}).get('passed_count')}/{(sub or {}).get('total_count')}")
        bad = check("student submits wrong solution", c.post("/api/practice/problems/balanced-brackets/submit", headers=candidate,
                                                           json={"language": "python", "code": "class Solution:\n    def isBalanced(self, s):\n        return True\n"}))
        step("wrong solution rejected", (bad or {}).get("verdict") == "WRONG_ANSWER", str((bad or {}).get("verdict")))
        check("student practice stats", c.get("/api/practice/stats/me", headers=candidate))
        check("RBAC: student blocked from problem authoring", c.get("/api/practice/admin/problems", headers=candidate), (401, 403))
        admin_list = check("admin lists practice problems", c.get("/api/practice/admin/problems", headers=admin))
        pid = next(p["id"] for p in admin_list if p["slug"] == "balanced-brackets")
        report = check("admin validates reference solution", c.post(f"/api/practice/admin/problems/{pid}/validate", headers=admin))
        step("reference solution passes every test", (report or {}).get("ok") is True, (report or {}).get("message", ""))

    failed = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} steps passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
