---
name: practice-problems
description: Author, validate or debug LeetCode-style practice problems in ExamSentinel (judge modes, function specs, test data, the Piston harness). Use when adding problems to the bank, a problem fails validation, or a student reports a wrong verdict.
argument-hint: "[problem-slug]"
allowed-tools: Bash, Read, Edit
---

# Practice problems

Code: `backend/app/services/practice_judge.py` (judge + harness), `backend/app/api/practice.py` (API),
`backend/practice_bank/` (problem definitions: `core`, `algorithms`, `sql`) + `backend/seed_practice.py` (seeder), `frontend/app/candidate/problems/` (student UI), `frontend/app/admin/problems/` (authoring UI).

## Two answer styles

| `judge_mode` | Student writes | Test input | Expected |
|---|---|---|---|
| `FUNCTION` | a method on `class Solution` | one compact JSON value **per parameter line** | one JSON value |
| `STDIO` | a full program reading stdin | raw stdin (≤ 128 KB) | stdout, trailing whitespace ignored |
| `SQL` | one SQLite `SELECT` | `INSERT`s for that dataset (schema in `sql_schema`) | JSON array of rows; any order unless `compare_mode="exact"` |

`function_spec` types: `int long double bool string`, their `[]` arrays, `int[][]`, `string[][]`.
`compare_mode`: `exact`, `unordered` (list in any order), `float` (1e-5).

## Adding problems

Prefer adding a `problem(...)` (or `sql_problem(...)`) call in `backend/practice_bank/`. Append to the
**end** of a module — every module draws from one seeded RNG, so inserting earlier changes others' hidden data. write the statement **in your own words**
(never copy LeetCode text), a Python reference solution, sample args (with explanations) and hidden args.
Expected outputs are computed by running the reference — never hand-write them.

Rules that validation has caught before:
- Every input must have exactly **one** correct answer (or use `compare="unordered"`/`"float"`).
- Hidden-case tuples hold the *arguments*: `([1, 2], 3)` for two params, `(5,)` for one — not `((5,),)`.
- Keep `long` results below 2^53 so JavaScript numbers stay exact.
- SQL is judged on **SQLite 3.36** (Piston) while expected rows are computed with Python's newer SQLite.
  Validation catches divergences — e.g. 3.36 mis-evaluates `DISTINCT … LIMIT/OFFSET` in a subquery.
  Never name a table `argv` (the runner creates it).

Then:
```bash
cd backend && ../.venv/Scripts/python.exe seed_practice.py
```
and validate (admin UI: Practice Problems → shield icon, or `POST /api/practice/admin/problems/{id}/validate`).
A problem is only ready when its reference passes **every** test on the real engine.

## How the judge runs code

All cases go in **one** Piston execution: the generated harness reads `es_input.txt` (sent base64 so gcc
doesn't compile it, and as a file because Piston truncates stdin past ~200 kB), calls the method per case,
and prints `@@ES@@{json}` lines with result, captured stdout and per-case ms. Java's single-file launcher
runs the first class, so `Main` is emitted before the student's `Solution`.

## Using a problem in an exam

Admin → Practice Problems → clipboard icon (`POST /api/practice/admin/problems/{id}/to-exam`) creates a
CODING/SQL question whose `correct_answer` is `{"practice_problem_id": …}`. Candidates' **Run** uses the
sample tests (`POST /api/practice/exam-run`); grading runs every test and awards points × passed/total.

## Difficulty

Set by the author; the admin list shows "Students find it …" once 20+ submissions put acceptance outside
the band (≥ 60% Easy, 35–60% Medium, < 35% Hard).

## Debugging a wrong verdict

1. Reproduce with `judge()` directly (see `tests/test_practice.py::test_real_engine_*`).
2. `COMPILE_ERROR` on every language → check the harness template for that language.
3. Verdicts on big inputs only → Piston limits (`docker-compose.piston.yml`: run timeout 10 s, output 8 MB).
4. Add a regression test to `tests/test_practice.py`.
