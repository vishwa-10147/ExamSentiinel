---
name: practice-problems
description: Author, validate or debug LeetCode-style practice problems in ExamSentinel (judge modes, function specs, test data, the Piston harness). Use when adding problems to the bank, a problem fails validation, or a student reports a wrong verdict.
argument-hint: "[problem-slug]"
allowed-tools: Bash, Read, Edit
---

# Practice problems

Code: `backend/app/services/practice_judge.py` (judge + harness), `backend/app/api/practice.py` (API),
`backend/seed_practice.py` (bank), `frontend/app/candidate/problems/` (student UI), `frontend/app/admin/problems/` (authoring UI).

## Two answer styles

| `judge_mode` | Student writes | Test input | Expected |
|---|---|---|---|
| `FUNCTION` | a method on `class Solution` | one compact JSON value **per parameter line** | one JSON value |
| `STDIO` | a full program reading stdin | raw stdin (≤ 128 KB) | stdout, trailing whitespace ignored |

`function_spec` types: `int long double bool string`, their `[]` arrays, `int[][]`, `string[][]`.
`compare_mode`: `exact`, `unordered` (list in any order), `float` (1e-5).

## Adding problems

Prefer adding to `PROBLEMS` in `backend/seed_practice.py`: write the statement **in your own words**
(never copy LeetCode text), a Python reference solution, sample args (with explanations) and hidden args.
Expected outputs are computed by running the reference — never hand-write them.

Rules that validation has caught before:
- Every input must have exactly **one** correct answer (or use `compare="unordered"`/`"float"`).
- Hidden-case tuples hold the *arguments*: `([1, 2], 3)` for two params, `(5,)` for one — not `((5,),)`.
- Keep `long` results below 2^53 so JavaScript numbers stay exact.

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

## Debugging a wrong verdict

1. Reproduce with `judge()` directly (see `tests/test_practice.py::test_real_engine_*`).
2. `COMPILE_ERROR` on every language → check the harness template for that language.
3. Verdicts on big inputs only → Piston limits (`docker-compose.piston.yml`: run timeout 10 s, output 8 MB).
4. Add a regression test to `tests/test_practice.py`.
