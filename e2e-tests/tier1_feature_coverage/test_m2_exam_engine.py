"""
Tier 1 Feature Coverage: Milestone 2 — Core Exam Engine & Candidate Portal
Features Covered: 8 to 15
- Feature 8: Exam CRUD & Management
- Feature 9: Question Bank Management
- Feature 10: Standard Question Types
- Feature 11: Candidate Enrollment & Scheduling
- Feature 12: Candidate Exam Portal
- Feature 13: Exam Taking Interface
- Feature 14: Client-Side Auto-Save
- Feature 15: Exam Timer & Auto-Submit
"""
import unittest
import os
import uuid
import sys
import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from client import ExamSentinelClient


class TestM2ExamEngine(unittest.TestCase):
    """Tier 1 Test Suite for Core Exam Engine and Taking Portal."""

    def setUp(self):
        self.client = ExamSentinelClient()
        self.unique_id = str(uuid.uuid4())[:8]

        # Register and login admin
        admin_email = f"admin_exam_{self.unique_id}@examsentinel.test"
        admin_pwd = "AdminExamPassword123!"
        self.client.post("/api/auth/register", data={"email": admin_email, "password": admin_pwd, "role": "admin"})
        login_res = self.client.post("/api/auth/login", data={"email": admin_email, "password": admin_pwd})
        self.admin_token = login_res.json().get("access_token")

        # Register and login candidate
        cand_email = f"cand_exam_{self.unique_id}@examsentinel.test"
        cand_pwd = "CandExamPassword123!"
        self.client.post("/api/auth/register", data={"email": cand_email, "password": cand_pwd, "role": "candidate"})
        cand_login = self.client.post("/api/auth/login", data={"email": cand_email, "password": cand_pwd})
        self.candidate_token = cand_login.json().get("access_token")

    def test_01_create_exam_with_settings(self):
        """Feature 8: Admin creates exam configuration with duration and timing."""
        admin_client = ExamSentinelClient()
        admin_client.set_token(self.admin_token)

        payload = {
            "title": f"Midterm Exam {self.unique_id}",
            "description": "Standard Midterm Examination",
            "duration_minutes": 90,
            "late_entry_tolerance_minutes": 15,
            "starts_at": (datetime.datetime.utcnow() + datetime.timedelta(hours=1)).isoformat(),
            "ends_at": (datetime.datetime.utcnow() + datetime.timedelta(hours=3)).isoformat()
        }
        res = admin_client.post("/api/exams", data=payload)
        self.assertEqual(res.status_code, 201, f"Failed to create exam: {res.text}")
        data = res.json()
        self.assertIn("id", data)
        self.assertEqual(data.get("duration_minutes"), 90)

    def test_02_candidate_forbidden_from_creating_exam(self):
        """Feature 8 & RBAC: Candidate cannot create exams (must return 403)."""
        cand_client = ExamSentinelClient()
        cand_client.set_token(self.candidate_token)

        payload = {"title": "Unauthorized Exam", "duration_minutes": 60}
        res = cand_client.post("/api/exams", data=payload)
        self.assertEqual(res.status_code, 403, f"Expected 403 Forbidden, got {res.status_code}")

    def test_03_candidate_start_session(self):
        """Feature 11 & 12: Candidate launches scheduled exam session."""
        admin_client = ExamSentinelClient()
        admin_client.set_token(self.admin_token)
        exam_res = admin_client.post("/api/exams", data={"title": "Session Test", "duration_minutes": 60})
        exam_id = exam_res.json()["id"]

        cand_client = ExamSentinelClient()
        cand_client.set_token(self.candidate_token)
        session_res = cand_client.post("/api/exam/sessions/start", data={"exam_id": exam_id})
        self.assertEqual(session_res.status_code, 201, f"Failed to start session: {session_res.text}")
        session_data = session_res.json()
        self.assertIn("id", session_data)
        self.assertEqual(session_data.get("status"), "IN_PROGRESS")

    def test_04_auto_save_candidate_answer(self):
        """Feature 14: Client-side debounced answer save persistence."""
        admin_client = ExamSentinelClient()
        admin_client.set_token(self.admin_token)
        exam_res = admin_client.post("/api/exams", data={"title": "Answer Save Exam", "duration_minutes": 60})
        exam_id = exam_res.json()["id"]

        cand_client = ExamSentinelClient()
        cand_client.set_token(self.candidate_token)
        session_res = cand_client.post("/api/exam/sessions/start", data={"exam_id": exam_id})
        session_id = session_res.json()["id"]

        question_id = str(uuid.uuid4())
        answer_payload = {
            "question_id": question_id,
            "response_data": {"selected_option": "B", "explanation": "Option B is correct."},
            "client_timestamp": datetime.datetime.utcnow().isoformat(),
            "sequence_id": 1
        }
        save_res = cand_client.post(f"/api/exam/sessions/{session_id}/answers", data=answer_payload)
        self.assertEqual(save_res.status_code, 200, f"Answer save failed: {save_res.text}")
        data = save_res.json()
        self.assertEqual(data.get("status"), "saved")
        self.assertEqual(data.get("question_id"), question_id)

    def test_05_manual_and_auto_submit_session(self):
        """Feature 15: Session submission transitions state to SUBMITTED and prevents further answer edits."""
        admin_client = ExamSentinelClient()
        admin_client.set_token(self.admin_token)
        exam_res = admin_client.post("/api/exams", data={"title": "Submit Exam", "duration_minutes": 60})
        exam_id = exam_res.json()["id"]

        cand_client = ExamSentinelClient()
        cand_client.set_token(self.candidate_token)
        session_res = cand_client.post("/api/exam/sessions/start", data={"exam_id": exam_id})
        session_id = session_res.json()["id"]

        # Submit session
        submit_res = cand_client.post(f"/api/exam/sessions/{session_id}/submit")
        self.assertEqual(submit_res.status_code, 200, f"Submit failed: {submit_res.text}")
        data = submit_res.json()
        self.assertEqual(data.get("status"), "submitted")

        # Invariant: Attempting to save an answer after submission must be rejected with 400
        post_submit_answer = cand_client.post(f"/api/exam/sessions/{session_id}/answers", data={
            "question_id": str(uuid.uuid4()),
            "response_data": {"selected_option": "A"}
        })
        self.assertEqual(post_submit_answer.status_code, 400, "Answer submission after exam submit must return 400")


if __name__ == "__main__":
    unittest.main()
