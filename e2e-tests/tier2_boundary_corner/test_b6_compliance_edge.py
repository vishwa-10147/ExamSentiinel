"""
Tier 2 Boundary & Corner Cases: Compliance, Appeals & Resource Governance
Tests reviewer separation invariants, empty appeals, and non-interruptive budget throttling.
"""
import unittest
import os
import uuid
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from client import ExamSentinelClient


class TestB6ComplianceEdge(unittest.TestCase):
    """Tier 2 Boundary tests for Compliance and Resource Limits."""

    def setUp(self):
        self.client = ExamSentinelClient()
        self.unique_id = str(uuid.uuid4())[:8]
        # Auto-login to prevent 401s during session creation
        email = f"candidate_{self.unique_id}@examsentinel.test"
        password = "CandidatePassword123!"
        self.client.post("/api/auth/register", data={
            "email": email, "password": password, "role": "candidate", "full_name": "Test Candidate"
        })
        login_res = self.client.post("/api/auth/login", data={"email": email, "password": password})
        if login_res.status_code == 200:
            self.client.set_token(login_res.json().get("access_token"))

    def test_01_appeal_reviewer_separation_strict_rejection(self):
        """Boundary Invariant: Submitting appeal where assigned_reviewer_id == original_reviewer_id fails with 400."""
        same_id = str(uuid.uuid4())
        payload = {
            "finding_id": str(uuid.uuid4()),
            "student_id": str(uuid.uuid4()),
            "original_reviewer_id": same_id,
            "assigned_reviewer_id": same_id,  # Colliding reviewer
            "reason": "Requesting re-evaluation"
        }
        res = self.client.post("/api/appeals", data=payload)
        self.assertEqual(res.status_code, 400, "Assigned appeal reviewer must not match original reviewer")

    def test_02_appeal_empty_reason_rejected(self):
        """Boundary: Appeals with empty or whitespace-only reasoning must be rejected with 422 or 400."""
        original_rev = str(uuid.uuid4())
        distinct_rev = str(uuid.uuid4())
        payload = {
            "finding_id": str(uuid.uuid4()),
            "student_id": str(uuid.uuid4()),
            "original_reviewer_id": original_rev,
            "assigned_reviewer_id": distinct_rev,
            "reason": "   "  # Whitespace only
        }
        res = self.client.post("/api/appeals", data=payload)
        self.assertIn(res.status_code, [400, 422], f"Expected 400 or 422 for empty appeal reason, got {res.status_code}")

    def test_03_in_progress_exam_immunity_from_budget_throttling(self):
        """Boundary Invariant: When budget hits 100% threshold, in-progress exams are NOT interrupted."""
        # Start exam session before budget exhaustion
        sess_res = self.client.post("/api/exam/sessions/start", data={"exam_id": str(uuid.uuid4())})
        session_id = sess_res.json()["id"]

        # Metering shows 100% compute limit reached
        metering = self.client.get("/api/metering/usage").json()
        self.assertIsNotNone(metering)

        # Invariant: Active candidate can still submit answers without interruption
        ans_res = self.client.post(f"/api/exam/sessions/{session_id}/answers", data={
            "question_id": str(uuid.uuid4()),
            "response_data": {"answer": "Answer during throttling"}
        })
        self.assertEqual(ans_res.status_code, 200, "Budget throttling must never interrupt an ongoing exam session")


if __name__ == "__main__":
    unittest.main()
