from datetime import datetime, timedelta, timezone
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.exam import Exam, ExamEnrollment, ExamEnrollmentStatus, ExamStatus
from app.models.institution import Institution
from app.models.question import ExamQuestion, Question, QuestionType
from app.models.response import ExamResponse
from app.models.session import ExamSession, SessionStatus
from app.models.user import User, UserRole


def auth_header(user: User) -> dict:
    token = create_access_token(
        data={
            "user_id": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "institution_id": str(user.institution_id) if user.institution_id else None,
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_question_crud_and_role_protection(
    async_client: AsyncClient,
    seed_users: list[User],
    test_institution: Institution,
):
    admin = next(u for u in seed_users if u.role == UserRole.ADMIN)
    candidate = next(u for u in seed_users if u.role == UserRole.CANDIDATE)

    # 1. Candidate cannot create question (403)
    cand_resp = await async_client.post(
        "/api/questions",
        headers=auth_header(candidate),
        json={
            "type": "MCQ_SINGLE",
            "title": "Unauthorized Question",
            "content_rich_text": "<p>What is 2+2?</p>",
            "points": 2.0,
        },
    )
    assert cand_resp.status_code == 403

    # 2. Admin creates question
    admin_resp = await async_client.post(
        "/api/questions",
        headers=auth_header(admin),
        json={
            "type": "MCQ_SINGLE",
            "title": "What is the capital of France?",
            "content_rich_text": "<p>Select the correct city:</p>",
            "options": [
                {"id": "a", "text": "London"},
                {"id": "b", "text": "Paris"},
                {"id": "c", "text": "Berlin"},
            ],
            "correct_answer": {"selected_option_ids": ["b"]},
            "points": 5.0,
            "difficulty": "EASY",
            "tags": ["geography", "europe"],
        },
    )
    assert admin_resp.status_code == 201
    q_data = admin_resp.json()
    q_id = q_data["id"]
    assert q_data["title"] == "What is the capital of France?"
    assert q_data["correct_answer"] == {"selected_option_ids": ["b"]}

    # 3. Admin lists questions
    list_resp = await async_client.get(
        "/api/questions",
        headers=auth_header(admin),
    )
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) >= 1
    assert any(q["id"] == q_id for q in items)

    # 4. Admin updates question
    upd_resp = await async_client.put(
        f"/api/questions/{q_id}",
        headers=auth_header(admin),
        json={"points": 10.0, "difficulty": "MEDIUM"},
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["points"] == 10.0
    assert upd_resp.json()["difficulty"] == "MEDIUM"


@pytest.mark.asyncio
async def test_exam_creation_and_validation(
    async_client: AsyncClient,
    seed_users: list[User],
    test_institution: Institution,
):
    admin = next(u for u in seed_users if u.role == UserRole.ADMIN)
    candidate = next(u for u in seed_users if u.role == UserRole.CANDIDATE)

    now = datetime.now(timezone.utc)
    start_time = now + timedelta(hours=1)
    end_time = now + timedelta(hours=3)

    # Candidate cannot create exam (403)
    cand_resp = await async_client.post(
        "/api/exams",
        headers=auth_header(candidate),
        json={
            "title": "Unauthorized Exam",
            "duration_minutes": 60,
            "start_window": start_time.isoformat(),
            "end_window": end_time.isoformat(),
        },
    )
    assert cand_resp.status_code == 403

    # Invalid end_window <= start_window
    inv_resp = await async_client.post(
        "/api/exams",
        headers=auth_header(admin),
        json={
            "title": "Invalid Window Exam",
            "duration_minutes": 60,
            "start_window": end_time.isoformat(),
            "end_window": start_time.isoformat(),
        },
    )
    assert inv_resp.status_code == 400

    # Valid exam creation
    create_resp = await async_client.post(
        "/api/exams",
        headers=auth_header(admin),
        json={
            "title": "Computer Science 101 Midterm",
            "description": "Comprehensive midterm exam covering algorithms",
            "duration_minutes": 90,
            "start_window": start_time.isoformat(),
            "end_window": end_time.isoformat(),
            "late_entry_minutes": 20,
        },
    )
    assert create_resp.status_code == 201
    exam = create_resp.json()
    assert exam["title"] == "Computer Science 101 Midterm"
    assert exam["status"] == "DRAFT"
    assert exam["duration_minutes"] == 90


@pytest.mark.asyncio
async def test_publish_guard_and_question_association(
    async_client: AsyncClient,
    seed_users: list[User],
    test_institution: Institution,
):
    admin = next(u for u in seed_users if u.role == UserRole.ADMIN)

    now = datetime.now(timezone.utc)
    start_time = now - timedelta(minutes=10)
    end_time = now + timedelta(hours=2)

    # 1. Create exam
    exam_resp = await async_client.post(
        "/api/exams",
        headers=auth_header(admin),
        json={
            "title": "Data Structures Final",
            "duration_minutes": 60,
            "start_window": start_time.isoformat(),
            "end_window": end_time.isoformat(),
            "late_entry_minutes": 15,
        },
    )
    exam_id = exam_resp.json()["id"]

    # 2. Publish guard: Cannot publish empty exam (400)
    pub_fail = await async_client.post(
        f"/api/exams/{exam_id}/publish",
        headers=auth_header(admin),
    )
    assert pub_fail.status_code == 400
    assert "no questions assigned" in pub_fail.json()["detail"]

    # 3. Create questions and assign
    q1_resp = await async_client.post(
        "/api/questions",
        headers=auth_header(admin),
        json={
            "type": "MCQ_SINGLE",
            "title": "Binary Tree Height",
            "content_rich_text": "<p>What is the worst-case height of an unbalanced BST?</p>",
            "options": [{"id": "1", "text": "O(log n)"}, {"id": "2", "text": "O(n)"}],
            "correct_answer": {"selected_option_ids": ["2"]},
            "points": 5.0,
        },
    )
    q1_id = q1_resp.json()["id"]

    assign_resp = await async_client.post(
        f"/api/exams/{exam_id}/questions",
        headers=auth_header(admin),
        json={"question_id": q1_id, "order_index": 1, "points_override": 7.5},
    )
    assert assign_resp.status_code == 201

    # 4. Now publish succeeds
    pub_ok = await async_client.post(
        f"/api/exams/{exam_id}/publish",
        headers=auth_header(admin),
    )
    assert pub_ok.status_code == 200
    assert pub_ok.json()["status"] == "PUBLISHED"
    assert pub_ok.json()["total_questions"] == 1
    assert pub_ok.json()["total_points"] == 7.5


@pytest.mark.asyncio
async def test_candidate_session_flow_and_hidden_answers(
    async_client: AsyncClient,
    seed_users: list[User],
    test_institution: Institution,
):
    admin = next(u for u in seed_users if u.role == UserRole.ADMIN)
    candidate = next(u for u in seed_users if u.role == UserRole.CANDIDATE)

    now = datetime.now(timezone.utc)
    start_time = now - timedelta(minutes=5)
    end_time = now + timedelta(hours=2)

    # 1. Admin creates question with secret correct answer
    q_resp = await async_client.post(
        "/api/questions",
        headers=auth_header(admin),
        json={
            "type": "MCQ_SINGLE",
            "title": "Complexity of QuickSort",
            "content_rich_text": "What is the average time complexity?",
            "options": [
                {"id": "opt_a", "text": "O(n log n)"},
                {"id": "opt_b", "text": "O(n^2)"},
            ],
            "correct_answer": {"secret_key": "opt_a"},
            "points": 4.0,
        },
    )
    q_id = q_resp.json()["id"]

    # 2. Admin creates and publishes exam
    exam_resp = await async_client.post(
        "/api/exams",
        headers=auth_header(admin),
        json={
            "title": "Algorithms 101",
            "duration_minutes": 45,
            "start_window": start_time.isoformat(),
            "end_window": end_time.isoformat(),
            "late_entry_minutes": 30,
        },
    )
    exam_id = exam_resp.json()["id"]

    await async_client.post(
        f"/api/exams/{exam_id}/questions",
        headers=auth_header(admin),
        json={"question_id": q_id, "order_index": 0},
    )
    await async_client.post(f"/api/exams/{exam_id}/publish", headers=auth_header(admin))

    # 3. Candidate not enrolled tries to start -> 403
    start_unauth = await async_client.post(
        "/api/exam/sessions/start",
        headers=auth_header(candidate),
        json={"exam_id": exam_id},
    )
    assert start_unauth.status_code == 403
    assert "not enrolled" in start_unauth.json()["detail"]

    # 4. Candidate enrolls
    enroll_resp = await async_client.post(
        f"/api/exams/{exam_id}/enroll",
        headers=auth_header(candidate),
        json={"candidate_ids": [str(candidate.id)]},
    )
    assert enroll_resp.status_code == 201

    # 5. Candidate starts session
    session_resp = await async_client.post(
        "/api/exam/sessions/start",
        headers=auth_header(candidate),
        json={"exam_id": exam_id},
    )
    assert session_resp.status_code == 200
    session_data = session_resp.json()
    session_id = session_data["session_id"]
    assert session_data["status"] == "IN_PROGRESS"
    assert session_data["total_questions"] == 1
    assert session_data["remaining_seconds"] > 0

    # Verify correct_answer is stripped from candidate view!
    q_candidate = session_data["questions"][0]
    assert "correct_answer" not in q_candidate
    assert q_candidate["id"] == q_id

    # 6. Auto-save answers (with sequence_id Last-Write-Wins)
    save_1 = await async_client.post(
        f"/api/exam/sessions/{session_id}/answers",
        headers=auth_header(candidate),
        json={
            "question_id": q_id,
            "response_data": {"selected_option_id": "opt_b"},
            "sequence_id": 1,
            "is_flagged": False,
        },
    )
    assert save_1.status_code == 200
    assert save_1.json()["status"] == "saved"

    # Save newer update
    save_2 = await async_client.post(
        f"/api/exam/sessions/{session_id}/answers",
        headers=auth_header(candidate),
        json={
            "question_id": q_id,
            "response_data": {"selected_option_id": "opt_a"},
            "sequence_id": 2,
            "is_flagged": True,
        },
    )
    assert save_2.status_code == 200
    assert save_2.json()["sequence_id"] == 2

    # Out-of-order stale save (sequence_id=1) must not overwrite sequence_id=2
    save_stale = await async_client.post(
        f"/api/exam/sessions/{session_id}/answers",
        headers=auth_header(candidate),
        json={
            "question_id": q_id,
            "response_data": {"selected_option_id": "opt_b"},
            "sequence_id": 1,
        },
    )
    assert save_stale.status_code == 200
    # Server retains latest sequence_id 2
    assert save_stale.json()["sequence_id"] == 2

    # Verify session state reflects latest save
    state_resp = await async_client.get(
        f"/api/exam/sessions/{session_id}",
        headers=auth_header(candidate),
    )
    assert state_resp.status_code == 200
    state = state_resp.json()
    assert state["answered_count"] == 1
    assert state["flagged_count"] == 1
    assert state["responses"][q_id]["response_data"] == {"selected_option_id": "opt_a"}
    assert state["responses"][q_id]["is_flagged"] is True

    # 7. Submit exam session
    sub_resp = await async_client.post(
        f"/api/exam/sessions/{session_id}/submit",
        headers=auth_header(candidate),
        json={"confirm": True},
    )
    assert sub_resp.status_code == 200
    assert sub_resp.json()["status"] == "submitted"

    # 8. Post-submission freeze: reject answers and re-submits (400)
    post_save = await async_client.post(
        f"/api/exam/sessions/{session_id}/answers",
        headers=auth_header(candidate),
        json={
            "question_id": q_id,
            "response_data": {"selected_option_id": "opt_b"},
            "sequence_id": 3,
        },
    )
    assert post_save.status_code == 400
    assert "already submitted" in post_save.json()["detail"]

    post_sub = await async_client.post(
        f"/api/exam/sessions/{session_id}/submit",
        headers=auth_header(candidate),
        json={"confirm": True},
    )
    assert post_sub.status_code == 400


@pytest.mark.asyncio
async def test_scheduling_window_and_late_entry_guards(
    async_client: AsyncClient,
    seed_users: list[User],
    test_institution: Institution,
):
    admin = next(u for u in seed_users if u.role == UserRole.ADMIN)
    candidate = next(u for u in seed_users if u.role == UserRole.CANDIDATE)
    now = datetime.now(timezone.utc)

    # 1. Exam in the future (not started yet)
    future_exam = await async_client.post(
        "/api/exams",
        headers=auth_header(admin),
        json={
            "title": "Future Exam",
            "duration_minutes": 30,
            "start_window": (now + timedelta(hours=1)).isoformat(),
            "end_window": (now + timedelta(hours=3)).isoformat(),
            "late_entry_minutes": 15,
        },
    )
    future_id = future_exam.json()["id"]
    # Add question and publish
    q = await async_client.post(
        "/api/questions",
        headers=auth_header(admin),
        json={"type": "SHORT_ANSWER", "title": "Q1", "content_rich_text": "Text", "points": 1.0},
    )
    await async_client.post(f"/api/exams/{future_id}/questions", headers=auth_header(admin), json={"question_id": q.json()["id"]})
    await async_client.post(f"/api/exams/{future_id}/publish", headers=auth_header(admin))
    await async_client.post(f"/api/exams/{future_id}/enroll", headers=auth_header(candidate), json={"candidate_ids": [str(candidate.id)]})

    # Start before start_window -> 403
    future_start = await async_client.post(
        "/api/exam/sessions/start",
        headers=auth_header(candidate),
        json={"exam_id": future_id},
    )
    assert future_start.status_code == 403
    assert "not opened yet" in future_start.json()["detail"]

    # 2. Exam with expired late entry window
    late_exam = await async_client.post(
        "/api/exams",
        headers=auth_header(admin),
        json={
            "title": "Late Entry Expired Exam",
            "duration_minutes": 30,
            "start_window": (now - timedelta(hours=1)).isoformat(),
            "end_window": (now + timedelta(hours=1)).isoformat(),
            "late_entry_minutes": 10,  # 10 mins late entry, but started 60 mins ago
        },
    )
    late_id = late_exam.json()["id"]
    await async_client.post(f"/api/exams/{late_id}/questions", headers=auth_header(admin), json={"question_id": q.json()["id"]})
    await async_client.post(f"/api/exams/{late_id}/publish", headers=auth_header(admin))
    await async_client.post(f"/api/exams/{late_id}/enroll", headers=auth_header(candidate), json={"candidate_ids": [str(candidate.id)]})

    late_start = await async_client.post(
        "/api/exam/sessions/start",
        headers=auth_header(candidate),
        json={"exam_id": late_id},
    )
    assert late_start.status_code == 403
    assert "Late entry window has expired" in late_start.json()["detail"]


@pytest.mark.asyncio
async def test_session_auto_expiration(
    async_client: AsyncClient,
    seed_users: list[User],
    test_institution: Institution,
):
    admin = next(u for u in seed_users if u.role == UserRole.ADMIN)
    candidate = next(u for u in seed_users if u.role == UserRole.CANDIDATE)
    now = datetime.now(timezone.utc)

    # Setup exam
    q = await async_client.post(
        "/api/questions",
        headers=auth_header(admin),
        json={"type": "SHORT_ANSWER", "title": "Exp Q", "content_rich_text": "Exp Content", "points": 1.0},
    )
    q_id = q.json()["id"]

    exam = await async_client.post(
        "/api/exams",
        headers=auth_header(admin),
        json={
            "title": "Quick Expire Exam",
            "duration_minutes": 10,
            "start_window": (now - timedelta(minutes=5)).isoformat(),
            "end_window": (now + timedelta(hours=1)).isoformat(),
            "late_entry_minutes": 15,
        },
    )
    exam_id = exam.json()["id"]
    await async_client.post(f"/api/exams/{exam_id}/questions", headers=auth_header(admin), json={"question_id": q_id})
    await async_client.post(f"/api/exams/{exam_id}/publish", headers=auth_header(admin))
    await async_client.post(f"/api/exams/{exam_id}/enroll", headers=auth_header(candidate), json={"candidate_ids": [str(candidate.id)]})

    # Start session
    session_resp = await async_client.post(
        "/api/exam/sessions/start",
        headers=auth_header(candidate),
        json={"exam_id": exam_id},
    )
    session_id = session_resp.json()["session_id"]

    # In background, simulate server_end_time passed 2 minutes ago
    try:
        from tests.conftest import test_async_session_maker
    except ImportError:
        from backend.tests.conftest import test_async_session_maker

    async with test_async_session_maker() as session:
        db_s = await session.get(ExamSession, uuid.UUID(session_id))
        db_s.server_end_time = now - timedelta(minutes=2)
        await session.commit()

    # Now attempt to save answer -> automatically triggers expiration and returns 400
    save_resp = await async_client.post(
        f"/api/exam/sessions/{session_id}/answers",
        headers=auth_header(candidate),
        json={
            "question_id": q_id,
            "response_data": {"text": "Late answer"},
            "sequence_id": 1,
        },
    )
    assert save_resp.status_code == 400
    assert "expired" in save_resp.json()["detail"].lower()

    # Get session state shows status = EXPIRED
    state_resp = await async_client.get(
        f"/api/exam/sessions/{session_id}",
        headers=auth_header(candidate),
    )
    assert state_resp.status_code == 200
    assert state_resp.json()["status"] == "EXPIRED"
    assert state_resp.json()["is_expired"] is True

    # A timer-triggered submit still finalizes a session already marked expired.
    submit_resp = await async_client.post(
        f"/api/exam/sessions/{session_id}/submit",
        headers=auth_header(candidate),
        json={"confirm": True},
    )
    assert submit_resp.status_code == 200
    assert submit_resp.json()["status"] == "submitted"


@pytest.mark.asyncio
async def test_answer_save_rejects_question_outside_exam(
    async_client: AsyncClient,
    seed_users: list[User],
    test_institution: Institution,
):
    admin = next(u for u in seed_users if u.role == UserRole.ADMIN)
    candidate = next(u for u in seed_users if u.role == UserRole.CANDIDATE)
    now = datetime.now(timezone.utc)

    assigned = await async_client.post(
        "/api/questions",
        headers=auth_header(admin),
        json={"type": "SHORT_ANSWER", "title": "Assigned", "content_rich_text": "Answer", "points": 1.0},
    )
    unassigned = await async_client.post(
        "/api/questions",
        headers=auth_header(admin),
        json={"type": "SHORT_ANSWER", "title": "Unassigned", "content_rich_text": "Do not answer", "points": 1.0},
    )
    exam = await async_client.post(
        "/api/exams",
        headers=auth_header(admin),
        json={
            "title": "Association Guard Exam",
            "duration_minutes": 30,
            "start_window": (now - timedelta(minutes=5)).isoformat(),
            "end_window": (now + timedelta(hours=1)).isoformat(),
            "late_entry_minutes": 15,
        },
    )
    exam_id = exam.json()["id"]
    await async_client.post(
        f"/api/exams/{exam_id}/questions",
        headers=auth_header(admin),
        json={"question_id": assigned.json()["id"]},
    )
    await async_client.post(f"/api/exams/{exam_id}/publish", headers=auth_header(admin))
    await async_client.post(
        f"/api/exams/{exam_id}/enroll",
        headers=auth_header(candidate),
        json={"candidate_ids": [str(candidate.id)]},
    )
    started = await async_client.post(
        "/api/exam/sessions/start",
        headers=auth_header(candidate),
        json={"exam_id": exam_id},
    )
    session_id = started.json()["session_id"]

    response = await async_client.post(
        f"/api/exam/sessions/{session_id}/answers",
        headers=auth_header(candidate),
        json={
            "question_id": unassigned.json()["id"],
            "response_data": {"text": "invalid"},
            "sequence_id": 1,
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Question is not part of this exam"


@pytest.mark.asyncio
async def test_session_cross_candidate_isolation(
    async_client: AsyncClient,
    seed_users: list[User],
    test_institution: Institution,
):
    admin = next(u for u in seed_users if u.role == UserRole.ADMIN)
    candidate_1 = next(u for u in seed_users if u.role == UserRole.CANDIDATE)

    # Register candidate 2 via API
    cand2_resp = await async_client.post(
        "/api/auth/register",
        json={
            "email": "candidate2@sentinel.edu",
            "password": "CandPass123!",
            "full_name": "Second Candidate",
            "role": "candidate",
            "institution_id": str(test_institution.id),
        },
    )
    assert cand2_resp.status_code == 201
    cand2_id = cand2_resp.json()["id"]

    token2_res = await async_client.post(
        "/api/auth/login",
        json={"email": "candidate2@sentinel.edu", "password": "CandPass123!"},
    )
    cand2_headers = {"Authorization": f"Bearer {token2_res.json()['access_token']}"}

    now = datetime.now(timezone.utc)
    q = await async_client.post(
        "/api/questions",
        headers=auth_header(admin),
        json={"type": "ESSAY", "title": "Essay Q", "content_rich_text": "Write essay", "points": 10.0},
    )
    exam = await async_client.post(
        "/api/exams",
        headers=auth_header(admin),
        json={
            "title": "Essay Exam",
            "duration_minutes": 60,
            "start_window": (now - timedelta(minutes=5)).isoformat(),
            "end_window": (now + timedelta(hours=1)).isoformat(),
            "late_entry_minutes": 15,
        },
    )
    exam_id = exam.json()["id"]
    await async_client.post(f"/api/exams/{exam_id}/questions", headers=auth_header(admin), json={"question_id": q.json()["id"]})
    await async_client.post(f"/api/exams/{exam_id}/publish", headers=auth_header(admin))

    # Enroll both
    await async_client.post(f"/api/exams/{exam_id}/enroll", headers=auth_header(candidate_1), json={"candidate_ids": [str(candidate_1.id)]})
    await async_client.post(f"/api/exams/{exam_id}/enroll", headers=cand2_headers, json={"candidate_ids": [cand2_id]})

    # Candidate 1 starts session
    s1 = await async_client.post(
        "/api/exam/sessions/start",
        headers=auth_header(candidate_1),
        json={"exam_id": exam_id},
    )
    session_1_id = s1.json()["session_id"]

    # Candidate 2 tries to access Candidate 1's session -> 403 Forbidden
    cross_get = await async_client.get(
        f"/api/exam/sessions/{session_1_id}",
        headers=cand2_headers,
    )
    assert cross_get.status_code == 403

    # Candidate 2 tries to post answer to Candidate 1's session -> 403 Forbidden
    cross_post = await async_client.post(
        f"/api/exam/sessions/{session_1_id}/answers",
        headers=cand2_headers,
        json={"question_id": q.json()["id"], "response_data": {"text": "hacked"}},
    )
    assert cross_post.status_code == 403


@pytest.mark.asyncio
async def test_session_resume_and_multitype_questions(
    async_client: AsyncClient,
    seed_users: list[User],
    test_institution: Institution,
):
    admin = next(u for u in seed_users if u.role == UserRole.ADMIN)
    candidate = next(u for u in seed_users if u.role == UserRole.CANDIDATE)
    now = datetime.now(timezone.utc)

    # Create MCQ_MULTI, SHORT_ANSWER, and ESSAY questions
    q_mcq_multi = await async_client.post(
        "/api/questions",
        headers=auth_header(admin),
        json={
            "type": "MCQ_MULTI",
            "title": "Select Prime Numbers",
            "content_rich_text": "<p>Select all prime numbers below:</p>",
            "options": [
                {"id": "opt_2", "text": "2"},
                {"id": "opt_4", "text": "4"},
                {"id": "opt_5", "text": "5"},
                {"id": "opt_9", "text": "9"},
            ],
            "correct_answer": {"selected_option_ids": ["opt_2", "opt_5"]},
            "points": 3.0,
        },
    )
    q1_id = q_mcq_multi.json()["id"]

    q_essay = await async_client.post(
        "/api/questions",
        headers=auth_header(admin),
        json={
            "type": "ESSAY",
            "title": "Explain CAP Theorem",
            "content_rich_text": "<p>Describe Consistency, Availability, and Partition tolerance.</p>",
            "rubric": {"max_words": 500, "criteria": ["Consistency", "Availability", "Partition Tolerance"]},
            "points": 10.0,
        },
    )
    q2_id = q_essay.json()["id"]

    # Create exam
    exam_res = await async_client.post(
        "/api/exams",
        headers=auth_header(admin),
        json={
            "title": "Distributed Systems Exam",
            "duration_minutes": 60,
            "start_window": (now - timedelta(minutes=5)).isoformat(),
            "end_window": (now + timedelta(hours=2)).isoformat(),
            "late_entry_minutes": 30,
        },
    )
    exam_id = exam_res.json()["id"]

    # Assign questions
    await async_client.post(f"/api/exams/{exam_id}/questions", headers=auth_header(admin), json={"question_id": q1_id, "order_index": 0})
    await async_client.post(f"/api/exams/{exam_id}/questions", headers=auth_header(admin), json={"question_id": q2_id, "order_index": 1})
    await async_client.post(f"/api/exams/{exam_id}/publish", headers=auth_header(admin))
    await async_client.post(f"/api/exams/{exam_id}/enroll", headers=auth_header(candidate), json={"candidate_ids": [str(candidate.id)]})

    # Candidate starts session
    start_1 = await async_client.post(
        "/api/exam/sessions/start",
        headers=auth_header(candidate),
        json={"exam_id": exam_id},
    )
    assert start_1.status_code == 200
    session_id = start_1.json()["session_id"]
    assert start_1.json()["total_questions"] == 2

    # Save MCQ_MULTI answer
    await async_client.post(
        f"/api/exam/sessions/{session_id}/answers",
        headers=auth_header(candidate),
        json={
            "question_id": q1_id,
            "response_data": {"selected_option_ids": ["opt_2", "opt_5"]},
            "sequence_id": 1,
        },
    )

    # Save ESSAY answer
    await async_client.post(
        f"/api/exam/sessions/{session_id}/answers",
        headers=auth_header(candidate),
        json={
            "question_id": q2_id,
            "response_data": {"text": "CAP theorem states that a distributed data store can simultaneously provide at most two of the three guarantees."},
            "sequence_id": 1,
        },
    )

    # Candidate reconnects/resumes session by calling start again -> resumes existing session without resetting answers
    resume_res = await async_client.post(
        "/api/exam/sessions/start",
        headers=auth_header(candidate),
        json={"exam_id": exam_id},
    )
    assert resume_res.status_code == 200
    resumed = resume_res.json()
    assert resumed["session_id"] == session_id
    assert resumed["answered_count"] == 2
    assert resumed["responses"][q1_id]["response_data"]["selected_option_ids"] == ["opt_2", "opt_5"]
    assert "CAP theorem states" in resumed["responses"][q2_id]["response_data"]["text"]
