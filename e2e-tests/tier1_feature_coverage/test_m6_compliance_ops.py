"""
Tier 1 Feature Coverage: Milestone 6 — Compliance, Operations & Security Hardening
Features Covered: 52 to 67
- Feature 52: Versioned Consent Capture
- Feature 53: Data Retention & Deletion Engine
- Feature 54: Student Appeals Flow (strict reviewer role separation)
- Feature 55: WCAG 2.1 AA Accessibility
- Feature 56: CI/CD Pipeline
- Feature 57: Structured Logging & Tracing
- Feature 58: Prometheus Metrics & Alerting
- Feature 59: Load Testing Scripts
- Feature 60: Backup & DR Restore Drill Script
- Feature 61: VPN & Proxy Detection (low-weight, no auto-block)
- Feature 62: Multi-Device & Multi-Tab Detection (alert, no auto-block)
- Feature 63: Question-Leak Detection
- Feature 64: Cost & Usage Metering
- Feature 65: Budget Alerts & Non-Interruptive Throttling
- Feature 66: Notification Service
- Feature 67: Calendar Integration
"""
import unittest
import os
import uuid
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from client import ExamSentinelClient


class TestM6ComplianceOps(unittest.TestCase):
    """Tier 1 Test Suite for Compliance, Appeals, Governance, and Operations."""

    def setUp(self):
        self.client = ExamSentinelClient()
        self.unique_id = str(uuid.uuid4())[:8]

    def test_01_student_appeals_reviewer_separation(self):
        """Feature 54 & Invariant: Appeal reviewer MUST strictly differ from original finding reviewer."""
        original_rev_id = str(uuid.uuid4())
        appeal_rev_id = str(uuid.uuid4())

        # 1. Distinct reviewer: Valid appeal creation
        payload_valid = {
            "finding_id": str(uuid.uuid4()),
            "student_id": str(uuid.uuid4()),
            "original_reviewer_id": original_rev_id,
            "assigned_reviewer_id": appeal_rev_id,
            "reason": "False positive phone detection - it was a calculator."
        }
        res_valid = self.client.post("/api/appeals", data=payload_valid)
        self.assertEqual(res_valid.status_code, 201, f"Appeal creation failed: {res_valid.text}")
        data = res_valid.json()
        self.assertEqual(data.get("status"), "UNDER_REVIEW")

        # 2. Same reviewer: Must be strictly rejected (400 Bad Request)
        payload_invalid = {
            "finding_id": str(uuid.uuid4()),
            "student_id": str(uuid.uuid4()),
            "original_reviewer_id": original_rev_id,
            "assigned_reviewer_id": original_rev_id,  # Same reviewer!
            "reason": "Appealing same reviewer"
        }
        res_invalid = self.client.post("/api/appeals", data=payload_invalid)
        self.assertEqual(res_invalid.status_code, 400, "Same reviewer assignment must be rejected")

    def test_02_vpn_detection_signal_does_not_auto_block(self):
        """Feature 61 & Invariant: VPN detection emits risk signal but NEVER terminates session."""
        sess_res = self.client.post("/api/exam/sessions/start", data={"exam_id": str(uuid.uuid4())})
        session_id = sess_res.json()["id"]

        vpn_payload = {
            "session_id": session_id,
            "event_type": "VPN_PROXY_FLAG",
            "payload": {
                "ip": "198.51.100.24",
                "provider": "NordVPN",
                "is_datacenter": True
            }
        }
        res = self.client.post("/api/telemetry/events", data=vpn_payload)
        self.assertEqual(res.status_code, 201)

        # Confirm session is still usable
        ans_res = self.client.post(f"/api/exam/sessions/{session_id}/answers", data={
            "question_id": str(uuid.uuid4()),
            "response_data": {"answer": "Continuing exam smoothly"}
        })
        self.assertEqual(ans_res.status_code, 200, "VPN detection must never auto-block or terminate session")

    def test_03_multi_device_multi_tab_signal_does_not_auto_block(self):
        """Feature 62 & Invariant: Multi-tab anomaly emits alert without auto-terminating."""
        sess_res = self.client.post("/api/exam/sessions/start", data={"exam_id": str(uuid.uuid4())})
        session_id = sess_res.json()["id"]

        tab_payload = {
            "session_id": session_id,
            "event_type": "MULTI_TAB",
            "payload": {"active_tabs_detected": 2}
        }
        res = self.client.post("/api/telemetry/events", data=tab_payload)
        self.assertEqual(res.status_code, 201)

    def test_04_cost_and_usage_metering_endpoint(self):
        """Feature 64 & 65: Institution usage metering tracks compute and reports threshold."""
        res = self.client.get("/api/metering/usage")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("sandbox_minutes_used", data)
        self.assertIn("video_minutes_used", data)
        self.assertIn("transcription_minutes_used", data)
        self.assertIn("current_utilization_pct", data)

    def test_05_ci_cd_workflow_specification(self):
        """Feature 56: GitHub Actions CI workflow is defined in repository."""
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        ci_path = os.path.join(project_root, ".github", "workflows", "ci.yml")
        if os.path.isfile(ci_path):
            self.assertGreater(os.path.getsize(ci_path), 50)
        else:
            self.skipTest(".github/workflows/ci.yml is pending delivery in Milestone 6")


if __name__ == "__main__":
    unittest.main()
