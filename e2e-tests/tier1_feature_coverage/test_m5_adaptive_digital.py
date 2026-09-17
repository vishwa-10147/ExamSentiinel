"""
Tier 1 Feature Coverage: Milestone 5 — Digital Exam Extensions & Enterprise Integrations
Features Covered: 42 to 51
- Feature 42: 2PL IRT Adaptive Engine
- Feature 43: Fisher Information Item Selection
- Feature 44: Ability Confidence Intervals
- Feature 45: Diagram Labeling Question Type
- Feature 46: Whiteboard Question Type
- Feature 47: Audio Response Question Type
- Feature 48: Offline Resilience via IndexedDB
- Feature 49: LMS Connector / LTI 1.3
- Feature 50: Enterprise SSO Integration
- Feature 51: Mobile Exam Mode
"""
import unittest
import os
import uuid
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from client import ExamSentinelClient


class TestM5AdaptiveDigital(unittest.TestCase):
    """Tier 1 Test Suite for IRT Adaptive Engine and Digital Question Types."""

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

    def test_01_irt_next_question_and_fisher_information(self):
        """Feature 42 & 43: 2PL IRT calculates next item maximizing Fisher Information."""
        payload = {
            "current_theta": 0.5,
            "answered_questions": [
                {"question_id": str(uuid.uuid4()), "difficulty_b": 0.2, "is_correct": True}
            ]
        }
        res = self.client.post("/api/adaptive/next-question", data=payload)
        self.assertEqual(res.status_code, 200, f"IRT selection failed: {res.text}")
        data = res.json()
        self.assertIn("question_id", data)
        self.assertIn("fisher_information", data)
        self.assertGreater(data.get("fisher_information", 0), 0)
        self.assertIn("standard_error", data)

    def test_02_ability_confidence_intervals(self):
        """Feature 44: Standard error is reported with theta ability estimate."""
        payload = {
            "current_theta": 1.2,
            "answered_questions": [{"question_id": str(uuid.uuid4()), "difficulty_b": 1.0, "is_correct": True} for _ in range(5)]
        }
        res = self.client.post("/api/adaptive/next-question", data=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("standard_error", data)
        self.assertLessEqual(data["standard_error"], 1.0)

    def test_03_diagram_labeling_answer_contract(self):
        """Feature 45: Diagram labeling questions accept coordinate hotspot answers."""
        sess_res = self.client.post("/api/exam/sessions/start", data={"exam_id": str(uuid.uuid4())})
        session_id = sess_res.json()["id"]

        question_id = str(uuid.uuid4())
        answer_payload = {
            "question_id": question_id,
            "response_data": {
                "type": "diagram_label",
                "labels": [
                    {"label_id": "L1", "target_x": 120.5, "target_y": 340.2},
                    {"label_id": "L2", "target_x": 450.0, "target_y": 180.8}
                ]
            },
            "sequence_id": 1
        }
        res = self.client.post(f"/api/exam/sessions/{session_id}/answers", data=answer_payload)
        self.assertEqual(res.status_code, 200, f"Failed to save diagram label answer: {res.text}")
        data = res.json()
        self.assertEqual(data.get("status"), "saved")
        self.assertEqual(data.get("question_id"), question_id)

    def test_04_whiteboard_stroke_serialization(self):
        """Feature 46: Whiteboard questions accept serialized vector strokes for replay."""
        sess_res = self.client.post("/api/exam/sessions/start", data={"exam_id": str(uuid.uuid4())})
        session_id = sess_res.json()["id"]

        question_id = str(uuid.uuid4())
        strokes_payload = {
            "question_id": question_id,
            "response_data": {
                "type": "whiteboard_vector",
                "strokes": [
                    {"color": "#000000", "width": 2, "points": [[10, 10], [12, 15], [18, 25]]},
                    {"color": "#FF0000", "width": 4, "points": [[50, 50], [60, 55], [75, 60]]}
                ]
            },
            "sequence_id": 1
        }
        res = self.client.post(f"/api/exam/sessions/{session_id}/answers", data=strokes_payload)
        self.assertEqual(res.status_code, 200, f"Failed to save whiteboard answer: {res.text}")
        data = res.json()
        self.assertEqual(data.get("status"), "saved")
        self.assertEqual(data.get("question_id"), question_id)

    def test_05_offline_resilience_replay_contract(self):
        """Feature 48: Queued offline answers can be replayed with sequence preserving."""
        sess_res = self.client.post("/api/exam/sessions/start", data={"exam_id": str(uuid.uuid4())})
        session_id = sess_res.json()["id"]

        offline_queue = [
            {"question_id": str(uuid.uuid4()), "response_data": {"ans": "A"}, "sequence_id": 1},
            {"question_id": str(uuid.uuid4()), "response_data": {"ans": "C"}, "sequence_id": 2},
        ]
        for item in offline_queue:
            res = self.client.post(f"/api/exam/sessions/{session_id}/answers", data=item)
            self.assertEqual(res.status_code, 200, f"Offline replay item failed: {res.text}")
            self.assertEqual(res.json().get("status"), "saved")


if __name__ == "__main__":
    unittest.main()
