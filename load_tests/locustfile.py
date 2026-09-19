import random
import uuid
import time
from locust import HttpUser, task, between

class StudentUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Simulate a student logging in."""
        self.email = f"loadtest_{uuid.uuid4().hex[:8]}@example.com"
        self.password = "Password123!"
        
        # 1. Register
        self.client.post("/api/auth/register", json={
            "email": self.email,
            "password": self.password,
            "full_name": "Load Tester",
            "role": "candidate"
        })
        
        # 2. Login
        response = self.client.post("/api/auth/login", data={
            "username": self.email,
            "password": self.password
        })
        
        if response.status_code == 200:
            token = response.json().get("access_token")
            self.client.headers.update({"Authorization": f"Bearer {token}"})
            self.session_id = str(uuid.uuid4())
        else:
            self.session_id = None

    @task(3)
    def fetch_exam(self):
        """Simulate fetching exam data."""
        self.client.get("/api/exams")

    @task(5)
    def submit_telemetry(self):
        """Simulate sending proctoring events."""
        if not self.session_id:
            return
            
        events = ["TAB_BLUR", "TAB_FOCUS", "RESIZE"]
        self.client.post("/api/proctoring/events", json={
            "session_id": self.session_id,
            "event_type": random.choice(events),
            "timestamp": int(time.time()),
            "details": {"source": "locust_load_test"}
        })

    @task(1)
    def execute_code(self):
        """Simulate submitting code to the sandbox."""
        if not self.session_id:
            return
            
        self.client.post("/api/code/execute", json={
            "session_id": self.session_id,
            "question_id": str(uuid.uuid4()),
            "language": "python",
            "source_code": "print('Load Test Success')"
        })
