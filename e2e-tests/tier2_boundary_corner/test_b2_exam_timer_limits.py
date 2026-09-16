"""
Tier 2 Boundary & Corner Cases: Exam Engine, Timer Limits & Payload Boundaries
Tests zero/negative durations, oversized answers, clock skew, and boundary submissions.
"""
import unittest
import os
import uuid
import sys
import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from client import ExamSentinelClient


class TestB2ExamTimerLimits(unittest.TestCase):
    """Tier 2 Boundary tests for Exam Duration and Answer Payload limits."""

    def setUp(self):
        self.client = ExamSentinelClient()
        self.unique_id = str(uuid.uuid4())[:8]

        # Register and login admin
        admin_email = f"admin_b2_{self.unique_id}@examsentinel.test"
        admin_pwd = "AdminB2Password123!"
        self.client.post("/api/auth/register", data={"email": admin_email, "password": admin_pwd, "role": "admin"})
        admin_login = self.client.post("/api/auth/login", data={"email": admin_email, "password": admin_pwd})
        self.admin_token = admin_login.json().get("access_token")

        self.admin_client = ExamSentinelClient()
        self.admin_client.set_token(self.admin_token)

    def test_01_negative_and_zero_duration_rejected(self):
        """Boundary: Exams with duration <= 0 must be rejected with 422 Unprocessable Entity."""
        invalid_durations = [0, -1, -60, -999]
        for dur in invalid_durations:
            res = self.admin_client.post("/api/exams", data={
                "title": f"Invalid Exam {dur}",
                "duration_minutes": dur
            })
            self.assertEqual(res.status_code, 422, f"Duration {dur} was not rejected with 422")

    def test_02_oversized_essay_submission_boundary(self):
        """Boundary: Extreme essay text (100,000 characters) is accepted or safely bounded."""
        exam_res = self.admin_client.post("/api/exams", data={"title": "Essay Exam", "duration_minutes": 60})
        exam_id = exam_res.json()["id"]

        sess_res = self.client.post("/api/exam/sessions/start", data={"exam_id": exam_id})
        session_id = sess_res.json()["id"]

        giant_essay = "Lorem ipsum dolor sit amet. " * 3500  # ~100,000 characters
        res = self.client.post(f"/api/exam/sessions/{session_id}/answers", data={
            "question_id": str(uuid.uuid4()),
            "response_data": {"essay_text": giant_essay},
            "sequence_id": 1
        })
        self.assertIn(res.status_code, [200, 413, 422], f"Unexpected status {res.status_code} for giant essay")

    def test_03_non_existent_session_returns_404(self):
        """Boundary: Submitting answers to invalid/non-existent session returns 404."""
        bogus_session_id = str(uuid.uuid4())
        res = self.client.post(f"/api/exam/sessions/{bogus_session_id}/answers", data={
            "question_id": str(uuid.uuid4()),
            "response_data": {"ans": "A"}
        })
        self.assertEqual(res.status_code, 404)

    def test_04_duplicate_submit_idempotence(self):
        """Boundary: Calling /submit twice on an already submitted session handles idempotency cleanly."""
        exam_res = self.admin_client.post("/api/exams", data={"title": "Idempotent Submit Exam", "duration_minutes": 60})
        exam_id = exam_res.json()["id"]

        sess_res = self.client.post("/api/exam/sessions/start", data={"exam_id": exam_id})
        session_id = sess_res.json()["id"]

        # First submit
        res1 = self.client.post(f"/api/exam/sessions/{session_id}/submit")
        self.assertEqual(res1.status_code, 200)

        # Second submit
        res2 = self.client.post(f"/api/exam/sessions/{session_id}/submit")
        self.assertIn(res2.status_code, [200, 400], "Duplicate submit must return 200 idempotent or 400 already submitted")


if __name__ == "__main__":
    unittest.main()
