# Staff Guide

How administrators, proctors and reviewers run assessments in ExamSentinel. For installation,
see [Installation](INSTALLATION.md).

## Contents

- [Roles](#roles)
- [Accounts](#accounts)
- [Building an exam](#building-an-exam)
- [Running an exam](#running-an-exam)
- [Reviewing integrity cases](#reviewing-integrity-cases)
- [Grading](#grading)
- [Coding practice problems](#coding-practice-problems)
- [Interviews](#interviews)
- [Exporting results](#exporting-results)

## Roles

| Role | Home page | Responsibilities |
|---|---|---|
| Admin | `/admin/dashboard` | Users, exams, question bank, practice problems, settings, audit log |
| Proctor | `/proctor/dashboard` | Live monitoring of running sessions, interviews |
| Reviewer | `/reviewer/dashboard` | Review queue, integrity decisions, grading approvals |
| Candidate | `/candidate/dashboard` | Taking exams, practice problems, results |

Every role is enforced by the API; the interface only hides what a role cannot use.

## Accounts

- **Single users** — *Admin → User Management → Create user*. A one-time password is shown
  once; share it with the user securely.
- **Bulk student import** — `POST /api/imports/students` with a CSV of `email`, `full_name`,
  `roll_number`. Because credentials are delivered by email, this requires email delivery to be
  configured (`ENABLE_EMAILS` and SMTP or provider settings).
- **Single sign-on** — when an OpenID Connect provider is configured (`SSO_*` settings), users
  sign in with their institutional account. `SSO_ALLOWED_DOMAINS` restricts who may sign in and
  `SSO_AUTO_PROVISION` controls whether first-time users are created automatically.
- Each account may have one active session; signing in elsewhere ends the previous session.

## Building an exam

1. Open *Admin → Exam Center* and create an exam: title, duration and the window in which it can
   be started.
2. Add questions from the question bank (*Admin → Question Bank*) or upload them on the exam's
   **Manage** page with **Upload Paper (CSV/JSON)**. CSV columns: `title`, `type`
   (e.g. `MCQ_SINGLE`, `CODING`, `SQL`, `ESSAY`), `content`, `points`, `difficulty`.
3. To use a coding problem from the practice bank, see
   [Using a practice problem in an exam](#using-a-practice-problem-in-an-exam).
4. Enrol candidates on the **Manage** page and publish the exam.

## Running an exam

Candidates complete a readiness check (camera and microphone) before starting. During the
session ExamSentinel records:

| Signal | Source |
|---|---|
| Tab switches, fullscreen exits, copy/paste | Browser telemetry |
| No face / multiple faces | BlazeFace in the candidate's browser |
| Phone or additional person in view | YOLO11n on webcam frames (server) |
| Concurrent sessions | Session management |

Signals are combined into a **risk score** (Low, Medium, High, Critical) using the weights in
*Admin → Settings*. At Medium or above a review case is opened. The score is **advisory**: it
never fails, penalises or blocks a candidate on its own.

Proctors follow running sessions in the **Proctor console** (`/proctor/dashboard`) and the live
grid, filter by risk level and see each candidate's latest signals.

## Reviewing integrity cases

Reviewers work through *Review Queue*. Each case shows the timeline of signals, webcam evidence
and the candidate's answers. The reviewer records the decision — the only point at which an
integrity outcome is set. Every decision is written to the audit log.

## Grading

- Objective questions are graded automatically.
- Coding questions are graded by running the answer against the question's tests in the
  sandbox; points are awarded in proportion to tests passed.
- Essays and other subjective answers are graded on the exam's **Grading** page. If
  `GEMINI_API_KEY` is configured, **Auto-Grade** proposes marks and feedback from the rubric.
  The proposal is a suggestion: review it and press **Save Grade** to record a mark.

## Coding practice problems

Students have a problem set of 116 data-structures and algorithms problems in 16 topics plus 11
SQL problems. Practice never affects exam results.

### Managing problems

1. Open *Admin → Practice Problems*. Each problem shows its permanent ID, topic, test counts,
   submissions and acceptance rate. After 20 or more submissions, a **suggested difficulty**
   based on the real acceptance rate is shown when it differs from the assigned one.
2. Create or edit a problem: statement, input/output format, constraints, expected complexity,
   editorial (shown to students only after they solve the problem), hints, answer style
   (function, stdin/stdout or SQL), starter code, reference solution and test cases. Mark two or
   three cases as visible samples.
3. Press **Validate** before publishing. The reference solution is run against every test on the
   execution engine, so incorrect test data is caught before students see it.
4. The built-in bank is maintained in the repository and loaded with `seed_practice.py`; see the
   [question bank guide](DSA_QUESTION_BANK.md).

### Using a practice problem in an exam

On a problem's row, select the clipboard icon (**Add to exam**), then choose the exam and the
points. This creates a coding question graded by the problem's full test suite. During the exam,
candidates can run the visible samples; when they submit, their answer is graded against every
test.

### What students see

Topic, difficulty and status filters, search by title or ID, an editor with **Run** (samples and
custom input) and **Submit** (all tests), verdicts, submission history and per-topic progress.
Hidden tests and reference solutions are never shown.

### Contests

*Admin → Contests* schedules a timed contest from practice problems.

1. Select **New contest**, enter a title, the start time (in your local time), the duration and
   the penalty for rejected attempts (default 5 minutes).
2. Add problems in the order they should appear (A, B, C, …) and set their points; harder
   problems default to more points. Problems that are unpublished in practice stay
   contest-only.
3. Tick **Published** when students should see the contest. They can register from then until
   it ends.

During the contest, students see a countdown, the problems, their score and a leaderboard that
refreshes every 15 seconds. Problems stay hidden until the start, editorials stay hidden until
the end, and submissions are accepted only from registered students inside the window. While a
contest is published and not over, its problems are also removed from the practice problem set.
After the start, the problems, points, timing and penalty are locked so results cannot be
rewritten; the title, description and visibility can still change.

## Interviews

*Admin → Interviews* schedules live interviews. Candidates give consent before the session;
interviewers record per-criterion scores and notes, and the conversation can be transcribed with
Whisper for later review.

## Exporting results

- *Admin → Analytics* exports scores and risk summaries as CSV.
- An exam's **Manage** page exports the candidate roster as CSV.
- *Admin → Audit Logs* exports the audit trail as CSV.

---

[Back to README](../README.md)
