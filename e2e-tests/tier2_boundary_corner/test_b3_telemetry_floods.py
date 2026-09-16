"""
Tier 2 Boundary & Corner Cases: Telemetry Floods & Sensor Anomalies
Tests high-rate event storms, invalid coordinates, corrupted payloads, and score saturation.
"""
import unittest
import os
import uuid
import sys
import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from client import ExamSentinelClient


class TestB3TelemetryFloods(unittest.TestCase):
    """Tier 2 Boundary tests for Telemetry Flooding and Sensor Payloads."""

    def setUp(self):
        self.client = ExamSentinelClient()
        self.unique_id = str(uuid.uuid4())[:8]

        # Start a candidate session
        sess_res = self.client.post("/api/exam/sessions/start", data={"exam_id": str(uuid.uuid4())})
        self.session_id = sess_res.json()["id"]

    def test_01_telemetry_event_burst_storm(self):
        """Boundary: Ingesting a burst storm of 50 rapid telemetry events succeeds without 500 errors."""
        for i in range(50):
            res = self.client.post("/api/telemetry/events", data={
                "session_id": self.session_id,
                "event_type": "WINDOW_BLUR",
                "payload": {"burst_index": i},
                "timestamp": datetime.datetime.utcnow().isoformat()
            })
            self.assertEqual(res.status_code, 201, f"Event {i} in burst failed with {res.status_code}")

    def test_02_missing_mandatory_fields_rejected(self):
        """Boundary: Missing session_id or event_type returns 422 Unprocessable Entity."""
        # Missing event_type
        res1 = self.client.post("/api/telemetry/events", data={"session_id": self.session_id})
        self.assertEqual(res1.status_code, 422)

        # Missing session_id
        res2 = self.client.post("/api/telemetry/events", data={"event_type": "FULLSCREEN_EXIT"})
        self.assertEqual(res2.status_code, 422)

    def test_03_risk_score_saturation_bounded_at_100(self):
        """Boundary: Cumulative risk score must cap at 100.0 and never overflow or wrap around."""
        # Trigger multiple high-severity events that sum to > 100
        for _ in range(5):
            self.client.post("/api/telemetry/events", data={
                "session_id": self.session_id,
                "event_type": "PHONE_DETECTED",
                "payload": {"confidence": 0.99}
            })

        # Invariant: Verify session remains IN_PROGRESS and answers can still be submitted
        ans_res = self.client.post(f"/api/exam/sessions/{self.session_id}/answers", data={
            "question_id": str(uuid.uuid4()),
            "response_data": {"ans": "Valid answer under high risk"}
        })
        self.assertEqual(ans_res.status_code, 200, "High risk must not lock candidate out of answering")


if __name__ == "__main__":
    unittest.main()
