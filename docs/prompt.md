# ExamSentinel Extension — AI Coding Agent Build Prompt

## Role
Implementing production-grade features on an existing platform. Read plan.md and explain.md fully before writing code.

## Ground Rules
1. Work one phase at a time (Phase 1 → 20). Don't start next phase until current demo checkpoint met.
2. Never guess at security-sensitive design (isolation, sandbox, auth/SSO).
3. Every new signal must reach the risk engine in the same change.
4. Never let AI output become a verdict — always human-reviewer-facing evidence.
5. Contract-first: API schemas + DB migration before UI/logic.
6. Backend before frontend, verified via /docs.
7. Feature-flag everything per exam/institution.
8. Test failure paths: timeouts, dropped calls, offline conflicts, cold-start IRT.

## Non-Negotiable Constraints
- No automated "cheating" verdicts
- No inference from demographics, appearance, disability, or emotion
- No plaintext secrets, no client-side-only auth checks
- No silent overclaiming of monitoring capability
- No student work lost on disconnect
- No untracked data collection
- No silent deletion or silent retention
- No decision without an appeal path
- No VPN/device/multi-tab signal may auto-block a student
- No budget enforcement may interrupt an exam in progress
- No production deploy without CI passing
- No claim of DR readiness without a tested restore
