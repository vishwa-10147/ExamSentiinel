# Code execution

How ExamSentinel runs untrusted code: the playground ("Run" with custom input), the
practice judge ("Run" against samples, "Submit" against every test), and coding
questions inside exams. Security properties are in [SECURITY.md](SECURITY.md).

## The engine

All user code runs in a **self-hosted [Piston](https://github.com/engineer-man/piston)**
instance (`infra/piston/`, `docker-compose.piston.yml`). The API process never executes
submissions: `app/services/sandbox_service.py` sends an HTTP request to `PISTON_URL` and
reads back stdout, stderr, exit code and status.

| Language | Piston runtime | Playground | STDIO problems | FUNCTION problems | SQL problems |
|---|---|---|---|---|---|
| Python | python 3.12 | yes | yes | yes | — |
| JavaScript | node 20 | yes | yes | yes | — |
| Java | java 15 | yes | yes | yes | — |
| C++ | gcc 10.2 (C++17) | yes | yes | yes | — |
| C | gcc 10.2 | yes | yes | **no** (see limitations) | — |
| SQL | sqlite3 3.36 | yes | — | — | yes |

Runtimes are installed into the `piston_packages` volume once:

```bash
docker compose -f docker-compose.piston.yml up -d
python scripts/install_piston_runtimes.py      # idempotent
```

The public `emkc.org` Piston API has been whitelist-only since 2026-02-15 — never point
`PISTON_URL` at it.

Engine settings (`docker-compose.piston.yml`): run timeout ≤ 10 s, compile timeout 15 s,
run memory 256 MB, compile memory 512 MB, 64 processes, 8 MB output. Our image
(`infra/piston/Dockerfile`) raises Piston's request-body limit from 100 kB to 8 MB because a
submission sends every test case in one request.

## Status values (`SandboxResult.status`)

| status | meaning | judge verdict |
|---|---|---|
| `success` | exited 0 | compared → `ACCEPTED` / `WRONG_ANSWER` |
| `error` | non-zero exit, signal, exception | `RUNTIME_ERROR` (Java "compilation failed" → `COMPILE_ERROR`) |
| `compile_error` | compile stage failed (C, C++) | `COMPILE_ERROR` |
| `timeout` | killed at the time limit | `TIME_LIMIT_EXCEEDED` |
| `memory_limit` | OOM-killed or allocator error | `MEMORY_LIMIT_EXCEEDED` |
| `output_limit` | printed more than the engine cap | `OUTPUT_LIMIT_EXCEEDED` |
| `system_error` | engine unreachable or rejected the job | `SYSTEM_ERROR` (not recorded as an attempt) |

## Run vs Submit

| | Playground `POST /api/sandbox/execute` | Run `POST /api/practice/problems/{slug}/run` | Submit `POST /api/practice/problems/{slug}/submit` |
|---|---|---|---|
| Input | your stdin | sample cases (+ optional custom input) | **all** cases, samples first |
| Output shown | stdout, stderr, compile output, exit code | per-case input/expected/output for samples and custom input | verdict, passed/total, runtime; for a failing **hidden** case only its number |
| Stored | no | no | yes (`practice_submissions`) |
| Stops early | — | no | at the first failing case |
| Rate limit (per IP, per path) | 30/min | 30/min | 10/min |

For custom input, the expected answer is computed by running the problem's reference
solution on the same input (server-side); the reference code itself is never sent.

## Judge modes (`app/services/practice_judge.py`)

### FUNCTION (LeetCode style)

The student implements a method on `class Solution`. The judge generates a harness per
language that:

1. reads `es_input.txt` — line 1 is the case count, then one JSON line per parameter per
   case. The file is sent **base64-encoded as an extra file**, not as stdin, because Piston
   truncates stdin past ~200 kB and gcc would otherwise try to compile a UTF-8 data file;
2. converts JSON to native values (`int[]` → `int[]`/`vector<int>`/list, …), including
   `ListNode` (JSON array → linked list) and `TreeNode` (level-order array with `null`s →
   binary tree). A `cycle` spec links the list tail back to node `pos` for cycle problems;
   `internal` parameters are part of the test input but not passed to the method;
3. calls the method once per case, timing it, catching exceptions per case;
4. prints one `@@ES@@{json}` record per case (`ok`, `result`, `ms`, captured stdout).

Supported types: `int long double bool string`, their 1-D arrays, `int[][]`, `string[][]`,
`ListNode`, `TreeNode`. A case slower than the problem's `time_limit_ms` is TLE even if the
whole run finished.

### STDIO

The program reads stdin and writes stdout; each case is a separate run (inputs are capped at
`MAX_STDIO_INPUT_BYTES` because of stdin truncation). Output is compared after trimming
trailing whitespace on each line.

### SQL

`schema + case INSERTs + .mode json + .bail on + student query` runs in sqlite3; the
resulting rows are compared with the expected rows. Exactly one result set is allowed.

## Comparison modes

| `compare_mode` | rule |
|---|---|
| `exact` | JSON-equal (`true` ≠ `1`) |
| `unordered` | same multiset of elements (elements compared canonically) |
| `float` | numbers (or lists of numbers) within 1e-5 absolute/relative |
| `checker` | the problem's `check(args, output, expected)` decides — for problems with many valid answers (e.g. #111 *Order the Tasks*) |

Checkers are Python functions stored with the problem. They run **inside the API process**,
so they may only come from the repository's question bank (`backend/practice_bank/`): the
admin API ignores a `checker` field and refuses `compare_mode: "checker"` for problems that
don't already have one. A checker that raises counts as a wrong answer.

## Expected outputs

Expected outputs are never written by hand. `backend/seed_practice.py` executes each
problem's reference solution through the **same generated Python harness** the judge uses
(locally, trusted code) to produce every expected output, and SQL references through Python's
`sqlite3`. `tests/test_sandbox_engine.py` then re-runs every reference on the real engine.

## Limitations

- **C is not available for FUNCTION-mode problems** (it is for STDIO problems and the
  playground). A C harness would need hand-written JSON parsing for every type.
- Runtime is wall-clock time measured inside the harness, so it varies with engine load; it
  is shown for information and only used for TLE against the per-case limit.
- Memory usage per case is not reported (the engine reports a whole-run figure only).
- One request carries all cases, so problems must keep their total test data under ~6 MB
  (8 MB body after base64). The largest problems (#109–#114) are sized for this.
