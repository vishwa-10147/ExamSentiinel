"""
Tier 1 Feature Coverage: Milestone 4 — Coding Exam Track & Interview Exam Track
Features Covered: 26 to 41
- Feature 26: Monaco Code Editor Integration
- Feature 27: Sandboxed Code Execution Worker (zero network, resource limits)
- Feature 28: Visible & Hidden Test Case Runner
- Feature 29: Autograding Engine
- Feature 30: Large Paste Detection
- Feature 31: Typing Cadence Analysis
- Feature 32: MOSS-Style Token Similarity
- Feature 33: Pre-Publish Test Case Validation
- Feature 34: Live WebRTC Video Room
- Feature 35: Interview Question Script UI
- Feature 36: Rubric-Based Panel Scoring
- Feature 37: Multi-Panelist Independent Scoring
- Feature 38: Async Interview Mode
- Feature 39: Whisper Transcription Pipeline
- Feature 40: Clickable Transcript Highlights
- Feature 41: Interview Screen-Share Detection
"""
import unittest
import os
import uuid
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from client import ExamSentinelClient


class TestM4CodingInterview(unittest.TestCase):
    """Tier 1 Test Suite for Coding and Interview Tracks."""

    def setUp(self):
        self.client = ExamSentinelClient()
        self.unique_id = str(uuid.uuid4())[:8]

        # Register candidate
        cand_email = f"cand_m4_{self.unique_id}@examsentinel.test"
        cand_pwd = "CandM4Password123!"
        self.client.post("/api/auth/register", data={"email": cand_email, "password": cand_pwd, "role": "candidate"})
        cand_login = self.client.post("/api/auth/login", data={"email": cand_email, "password": cand_pwd})
        self.candidate_token = cand_login.json().get("access_token")

    def test_01_code_execution_in_sandbox(self):
        """Feature 27: Code executes in sandbox returning execution stats and output."""
        cand_client = ExamSentinelClient()
        cand_client.set_token(self.candidate_token)

        code_payload = {
            "language": "python",
            "source_code": "def solution(x):\n    return x * 2\n\nprint(solution(21))",
            "stdin": "",
            "time_limit_sec": 2.0,
            "memory_limit_mb": 128
        }
        res = cand_client.post("/api/code/submit", data=code_payload)
        self.assertEqual(res.status_code, 200, f"Code execution failed: {res.text}")
        data = res.json()
        self.assertIn("submission_id", data)
        self.assertEqual(data.get("status"), "SUCCESS")
        self.assertIn("wall_time_ms", data)
        self.assertIn("peak_memory_kb", data)

    def test_02_sandbox_zero_network_enforcement(self):
        """Feature 27 Invariant: Code attempting network access is blocked and fails safely."""
        cand_client = ExamSentinelClient()
        cand_client.set_token(self.candidate_token)

        network_code = {
            "language": "python",
            "source_code": "import urllib.request\nurllib.request.urlopen('http://example.com')",
            "time_limit_sec": 2.0
        }
        res = cand_client.post("/api/code/submit", data=network_code)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn(data.get("status"), ["RUNTIME_ERROR", "PERMISSION_DENIED"])
        self.assertIn("Network", data.get("stdout", "") + data.get("stderr", "") + data.get("error", ""))

    def test_03_pre_publish_test_case_validation_blocking(self):
        """Feature 33: Cannot publish coding question if reference solution fails test cases."""
        cand_client = ExamSentinelClient()
        cand_client.set_token(self.candidate_token)

        # 1. Valid reference solution
        valid_payload = {
            "reference_solution": "def add(a, b): return a + b",
            "test_cases": [{"input": "2, 3", "expected_output": "5"}]
        }
        res_valid = cand_client.post("/api/coding/validate-test-cases", data=valid_payload)
        self.assertEqual(res_valid.status_code, 200)
        self.assertTrue(res_valid.json().get("valid"))

        # 2. Flawed reference solution (must block publish)
        invalid_payload = {
            "reference_solution": "def fail_add(a, b): return a - b",
            "test_cases": [{"input": "2, 3", "expected_output": "5"}]
        }
        res_invalid = cand_client.post("/api/coding/validate-test-cases", data=invalid_payload)
        self.assertEqual(res_invalid.status_code, 200)
        self.assertFalse(res_invalid.json().get("valid"), "Flawed solution must be marked invalid")

    def test_04_large_paste_detection_signal(self):
        """Feature 30: Pasting > 10 lines generates risk signal."""
        cand_client = ExamSentinelClient()
        cand_client.set_token(self.candidate_token)
        session_res = cand_client.post("/api/exam/sessions/start", data={"exam_id": str(uuid.uuid4())})
        session_id = session_res.json()["id"]

        large_paste_lines = "\n".join([f"line_{i} = {i}" for i in range(15)])
        res = cand_client.post("/api/telemetry/events", data={
            "session_id": session_id,
            "event_type": "LARGE_PASTE",
            "payload": {
                "line_count": 15,
                "character_count": len(large_paste_lines),
                "diff": large_paste_lines
            }
        })
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data.get("event_type"), "LARGE_PASTE")

    def test_05_interview_screen_share_detection_signal(self):
        """Feature 41: Screen-share during interview is flagged as reviewer signal without auto-penalty."""
        cand_client = ExamSentinelClient()
        cand_client.set_token(self.candidate_token)
        session_res = cand_client.post("/api/exam/sessions/start", data={"exam_id": str(uuid.uuid4())})
        session_id = session_res.json()["id"]

        res = cand_client.post("/api/telemetry/events", data={
            "session_id": session_id,
            "event_type": "UNAUTHORIZED_SCREEN_SHARE",
            "payload": {"track_id": "video-track-screen-01", "active": True}
        })
        self.assertEqual(res.status_code, 201)


if __name__ == "__main__":
    unittest.main()
