# API reference — practice & code execution

Base URL `http://localhost:8000` (all routes are under `/api`). Interactive docs for every
route: `http://localhost:8000/docs` (Swagger) and `/redoc`. This page covers the practice
platform and the code runner; the examples are real responses from a local instance.

## Authentication

```http
POST /api/auth/login
Content-Type: application/json

{"email": "candidate@sentinel.edu", "password": "DemoPass123!"}
```

```json
{"access_token": "eyJ…", "refresh_token": "eyJ…", "token_type": "bearer", "expires_in": 1800,
 "user": {"id": "991b7ca9-…", "email": "candidate@sentinel.edu", "role": "candidate", "…": "…"}}
```

Send `Authorization: Bearer <access_token>` on every request below. (The demo password
comes from `seed_admin.py` and exists only in development seeds.) Logging in again revokes
the previous session's token. Refresh with `POST /api/auth/refresh`.

## Student endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/practice/problems` | list published problems with your status |
| GET | `/api/practice/topics` | topics in syllabus order with your solved/attempted/total |
| GET | `/api/practice/tags` | all tags |
| GET | `/api/practice/problems/{slug}` | problem detail (samples only) |
| POST | `/api/practice/problems/{slug}/run` | run against samples (+ custom input); not stored |
| POST | `/api/practice/problems/{slug}/submit` | judge against all tests; stored |
| GET | `/api/practice/problems/{slug}/submissions` | your submissions for one problem (with code) |
| GET | `/api/practice/submissions` | your whole submission history (no code), paginated |
| GET | `/api/practice/stats/me` | totals, per-difficulty, per-topic, streak, activity |
| GET | `/api/practice/leaderboard` | weighted solved counts |
| POST | `/api/sandbox/execute` | playground: run any program with stdin |

### List problems

`GET /api/practice/problems?topic=Heaps&sort=difficulty`

Query parameters: `difficulty` (`EASY`/`MEDIUM`/`HARD`), `topic`, `tag`, `status`
(`solved`/`attempted`/`todo`), `search` (title, slug, tag, or `#ID`), `sort`
(`number` default, `difficulty`, `acceptance`, `title`).

```json
{
  "items": [
    {"id": "3807a025-…", "number": 101, "topic": "Heaps", "slug": "smash-stones", "title": "Smash the Stones",
     "difficulty": "EASY", "tags": ["heap", "simulation"], "acceptance_rate": null, "status": "todo"},
    {"id": "e2c32b3d-…", "number": 16, "topic": "Heaps", "slug": "k-most-frequent", "title": "K Most Frequent Values",
     "difficulty": "MEDIUM", "tags": ["…"], "acceptance_rate": null, "status": "todo"}
  ],
  "total": 4
}
```

### Problem detail

`GET /api/practice/problems/task-ordering` returns `number`, `topic`, `statement`,
`input_format`, `output_format`, `constraints`, `complexity`, `hints`, `examples`
(samples only), `starter_code` per language, `languages`, `time_limit_ms`,
`memory_limit_mb`, `function_spec`, `compare_mode`, `status`, `has_editorial` and
`editorial`. **`editorial` is `null` until you have an accepted submission** (admins always
see it). Hidden tests, reference solutions and checkers are never included.

### Run

```http
POST /api/practice/problems/lone-value/run
{"language": "python", "code": "class Solution:\n    def loneValue(self, nums):\n        r = 0\n        for x in nums:\n            r ^= x\n        return r\n",
 "custom_input": "[9,4,9]"}
```

`language` is one of the problem's `languages`. For FUNCTION problems `custom_input` is one
JSON value per parameter per line; its expected output is computed from the reference.

```json
{
  "verdict": "ACCEPTED",
  "cases": [
    {"index": 0, "passed": true, "input": "[2,2,1]", "expected": "1", "output": "1", "stdout": "", "runtime_ms": 0.0, "error": null, "is_custom": false},
    {"index": 1, "passed": true, "input": "[4,1,2,1,2]", "expected": "4", "output": "4", "stdout": "", "runtime_ms": 0.0, "error": null, "is_custom": false},
    {"index": 2, "passed": true, "input": "[-7]", "expected": "-7", "output": "-7", "stdout": "", "runtime_ms": 0.0, "error": null, "is_custom": false},
    {"index": 3, "passed": true, "input": "[9,4,9]", "expected": "4", "output": "4", "stdout": "", "runtime_ms": 0.0, "error": null, "is_custom": true}
  ],
  "passed_count": 4, "total_count": 4, "runtime_ms": 0, "compile_output": null, "error": null
}
```

### Submit

```http
POST /api/practice/problems/lone-value/submit
{"language": "cpp", "code": "class Solution { public: int loneValue(vector<int>& nums) { return nums[0]; } };"}
```

```json
{
  "id": "582ddc92-…", "problem_id": "4596ea0b-…", "language": "cpp",
  "verdict": "WRONG_ANSWER", "passed_count": 0, "total_count": 5, "runtime_ms": null,
  "failure": {"case_number": 1, "is_sample": true, "passed": false, "input": "[2,2,1]", "expected": "1",
              "output": "2", "stdout": "", "runtime_ms": 0.01, "error": null},
  "created_at": "2026-10-14T17:43:08.526758", "source_code": null, "compile_output": null
}
```

Judging stops at the first failing case. When that case is **hidden**, `input`,
`expected` and `output` are `null` — only `case_number` is revealed.

Verdicts: `ACCEPTED`, `WRONG_ANSWER`, `TIME_LIMIT_EXCEEDED`, `MEMORY_LIMIT_EXCEEDED`,
`OUTPUT_LIMIT_EXCEEDED`, `RUNTIME_ERROR`, `COMPILE_ERROR`, `SYSTEM_ERROR` (engine
unavailable — not stored as an attempt).

### Submission history

`GET /api/practice/submissions?verdict=ACCEPTED&limit=50&offset=0`

```json
{"items": [{"id": "582ddc92-…", "problem_number": 116, "problem_slug": "lone-value", "problem_title": "The Lone Value",
            "language": "cpp", "verdict": "WRONG_ANSWER", "passed_count": 0, "total_count": 5,
            "runtime_ms": null, "created_at": "2026-10-14T17:43:08.526758"}],
 "total": 25}
```

### Progress

`GET /api/practice/topics` →
`[{"topic": "Arrays", "solved": 2, "attempted": 0, "total": 12}, {"topic": "Strings", …}, …]`.
`GET /api/practice/stats/me` includes the same list as `by_topic`, plus `solved_total`,
`problems_total`, `by_difficulty`, `submissions_total`, `acceptance_rate`,
`current_streak_days`, `activity` (date → count) and `recent`.

### Playground (custom programs)

```http
POST /api/sandbox/execute
{"language": "c", "code": "#include <stdio.h>\nint main(void) {\n    int a, b;\n    scanf(\"%d %d\", &a, &b);\n    printf(\"%d\\n\", a + b);\n    return 0;\n}\n",
 "stdin": "2 40\n"}
```

```json
{"status": "success", "stdout": "42\n", "stderr": "", "compile_output": "", "exit_code": 0,
 "test_results": null, "wall_time_ms": 504, "time_limit_ms": 5000, "memory_limit_mb": 256}
```

A compile error (`return 0` without `;`):

```json
{"status": "compile_error", "stdout": "", "stderr": "",
 "compile_output": "main.c.c: In function 'main':\nmain.c.c:3:13: error: expected ';' before '}' token\n …",
 "exit_code": 1, "wall_time_ms": 448, "time_limit_ms": 5000, "memory_limit_mb": 256}
```

`language`: `python`, `javascript`, `java` (define `public class Main`), `c`, `cpp` (or
`c++`), `sql`. Limits: code ≤ 50 000 characters, stdin ≤ 64 000, 5 s, 256 MB.
`status` is one of `success`, `error`, `compile_error`, `timeout`, `memory_limit`,
`output_limit`, `system_error`.

## Admin endpoints (role `admin`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/practice/admin/problems` | all problems with test counts, acceptance, suggested difficulty |
| GET | `/api/practice/admin/problems/{id}` | full problem including tests and reference (never the checker) |
| POST | `/api/practice/admin/problems` | create (`number` must be unique → 409) |
| PUT | `/api/practice/admin/problems/{id}` | update |
| DELETE | `/api/practice/admin/problems/{id}` | delete |
| POST | `/api/practice/admin/problems/{id}/validate` | run the reference against every test on the engine |
| POST | `/api/practice/admin/problems/{id}/to-exam` | create an exam question judged by this problem's tests |

The upsert body accepts `slug`, `number`, `topic`, `title`, `difficulty`, `tags`,
`statement`, `input_format`, `output_format`, `constraints`, `complexity`, `editorial`,
`hints`, `judge_mode`, `function_spec`, `sql_schema`, `compare_mode`, `starter_code`,
`reference_solution`, `time_limit_ms`, `memory_limit_mb`, `is_published`, `test_cases`.
A `checker` field is ignored; `compare_mode: "checker"` is refused unless the problem
already has a bank checker.

## Exam integration

`POST /api/practice/exam-run` (candidate, during an exam session) runs a practice-backed
exam question against its samples. Final grading happens on submit via
`grading_service`, which judges the answer against all of the problem's tests.

## Errors

| Status | When |
|---|---|
| 401 | missing/expired token |
| 403 | wrong role |
| 404 | unknown or unpublished problem |
| 409 | duplicate slug/number, problem without tests |
| 422 | invalid body (size limits, bad custom input, unsupported language for the problem) |
| 429 | rate limit, or a run already in progress for this user |
