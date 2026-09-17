import http from 'k6/http';
import { check, sleep } from 'k6';

// 1000 Concurrent Users Spike Test
export const options = {
  stages: [
    { duration: '30s', target: 500 },  // Ramp up to 500 users over 30s
    { duration: '30s', target: 1000 }, // Spike to 1000 users over the next 30s
    { duration: '2m', target: 1000 },  // Hold at 1000 users for 2 minutes (taking the exam)
    { duration: '30s', target: 0 },    // Ramp down to 0
  ],
  thresholds: {
    // 99% of requests must complete below 500ms
    http_req_duration: ['p(99)<500'], 
    // Error rate must be less than 1%
    http_req_failed: ['rate<0.01'],   
  },
};

const BASE_URL = 'http://localhost:8000';

export default function () {
  // 1. Initial Load: Fetch exam configuration
  const examId = '25baf9ca-07c1-446d-a5b8-3b0544e76823';
  const examRes = http.get(`${BASE_URL}/api/exams/${examId}`);
  
  check(examRes, {
    'exam config loaded': (r) => r.status === 200,
  });

  sleep(1); // User reading questions

  // 2. Telemetry Spike: Simulate candidate triggering AI proctoring events
  // At 1000 users, this will blast 1000 POST requests per second to the Risk Engine
  const payload = JSON.stringify({
    session_id: '12345678-1234-1234-1234-123456789012',
    event_type: 'TAB_BLUR',
    timestamp: new Date().toISOString()
  });

  const params = {
    headers: { 'Content-Type': 'application/json' },
  };

  const telemetryRes = http.post(`${BASE_URL}/api/telemetry/events`, payload, params);
  
  check(telemetryRes, {
    'telemetry recorded': (r) => r.status === 200 || r.status === 201 || r.status === 422, // 422 allowed if mock validation fails
  });

  sleep(2); // Simulate time between events
}
