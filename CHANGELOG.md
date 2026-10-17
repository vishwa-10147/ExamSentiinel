# Changelog

Notable changes, newest first, summarised from the git history. The project has no tagged
releases yet; entries are grouped by date. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased

### Added
- Documentation: `SETUP.md` (moved from `docs/INSTALLATION.md`), a configuration reference,
  deployment, troubleshooting, and this changelog.

## 2026-10-16

### Fixed
- Docker Compose stack: the web app is built with its `NEXT_PUBLIC_*` values, and the web app no
  longer redirects HTTP to HTTPS itself (it redirected to `https://0.0.0.0:3000`). The front door
  (nginx or the load balancer) does that.

## 2026-10-15

### Added
- Campus server kit (`deploy/campus/`): one Linux server with HTTPS, nightly backups, restore and
  update scripts; webcam evidence on local disk behind signed links.
- Exam-day hardening: answers kept in the browser, retried and flushed before submit; one session
  per exam and candidate (migration 017); a submit is only shown once the server confirms it;
  CloudWatch metrics; keyboard and screen-reader access in the exam view.
- Production rehearsal of the AWS topology (`deploy/rehearsal/`), start-up checks that refuse
  unsafe production settings, and a migration/model drift check in CI.
- Several API processes share live events, interview rooms and run slots through Redis.
- Timed contests with registration, penalties and a live leaderboard.
- Practice judging queue: Submit waits up to 20 s, then the page polls.
- httpOnly cookie sessions, a per-account sign-in limit, and the MIT license.
- C support for function-style practice problems.
- A browser test that opens every page as every role.

### Changed
- One pooled HTTP client for the code engine: judging throughput from about 6 to 33 verdicts/s.
- Environment templates list only variables the code reads.
- Light and dark mode fixed across the app; one local launcher (`start-local.cmd`).

### Fixed
- Production problems found by the rehearsal: a crash parsing `CORS_ORIGINS`, client-IP spoofing
  through headers, database connection exhaustion under load, duplicate exam sessions from
  double starts, a time-out submit that showed success without the server, and more (see
  [Production readiness](docs/PRODUCTION_READINESS.md#problems-the-rehearsal-found)).
- A dead live-event listener when Redis timed out.

## 2026-10-14

### Added
- 116-problem DSA bank and 11 SQL problems on a self-hosted, verified code-execution engine.
- LeetCode-style practice platform, problem workspace and playground.
- Single sign-on (Google, Microsoft, generic OpenID Connect).
- Live interviews with WebRTC and faster-whisper transcripts.
- Playwright role tests.
- End-to-end AI cheating detection (in-browser face detection, optional YOLO phone/person
  detection), with advisory risk scores and human review.

### Changed
- Security hardening and an AWS deployment path.

## 2026-09-17 to 2026-10-04

Initial platform: authentication and roles, the exam builder, enrollment, the candidate exam
environment with timer and auto-save, objective auto-grading, results and leaderboards, the live
proctor dashboard, reviewer cases, user management, AI question generation, password-reset
e-mails, and many fixes found while using it.
