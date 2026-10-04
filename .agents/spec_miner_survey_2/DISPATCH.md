# Survey Task: Coding & Interview Exam Tracks (Phases 11–14)

## Objective
Thoroughly inspect and mine all requirements, specifications, schemas, endpoints, algorithms, constraints, and edge cases from `d:\vishwa47\v47Studio\ExamSentinel\ORIGINAL_REQUEST.md`.

## Focus Scope
1. Phases 11–12 (Coding Exam Track):
   - Monaco Editor integration (Python & JavaScript support, syntax highlighting, autocomplete)
   - Sandboxed Code Execution:
     * Isolation (containerized or process-isolated runner)
     * Resource limits (CPU limit, memory limit, timeout execution limits)
     * Security constraints (strictly no network access, filesystem jail)
     * Visible vs hidden test cases execution and grading
     * Pre-publish test case validation (blocking publish if reference solution fails or tests are invalid)
   - Coding Integrity & Plagiarism:
     * Large paste detection (>10 lines flagged with risk score)
     * Typing cadence analysis (keystroke interval distribution, burstiness detection, anomaly scoring)
     * MOSS-style tokenized cross-submission similarity detection (winnowing/k-gram tokenization, pairwise similarity indexing)
2. Phases 13–14 (Interview Exam Track):
   - Live WebRTC Video Room Integration (Signaling, peer connection, room management)
   - Question Script & Rubric-based panel scoring
   - Multi-panelist independent scoring & consensus aggregation
   - Async Interview Mode:
     * Timed recorded video/audio responses
     * Whisper-class transcription pipeline
     * Clickable timestamped highlights & transcript sync
   - Interview Screen-share detection & proctoring alerts

## Deliverables
Write your comprehensive analysis to:
- `d:\vishwa47\v47Studio\ExamSentinel\.agents\spec_miner_survey_2\survey_report.md`
- `d:\vishwa47\v47Studio\ExamSentinel\.agents\spec_miner_survey_2\handoff.md`

Notify the orchestrator via `send_message` when done.

## 2026-09-16T10:46:25Z
You are spec_miner_survey_2, working directory: d:\vishwa47\v47Studio\ExamSentinel\.agents\spec_miner_survey_2\
Read d:\vishwa47\v47Studio\ExamSentinel\ORIGINAL_REQUEST.md and d:\vishwa47\v47Studio\ExamSentinel\.agents\spec_miner_survey_2\DISPATCH.md.
Mine and extract all requirements, specifications, schemas, endpoints, algorithms, constraints, and edge cases for:
- Phases 11–12: Coding Exam Track (Monaco editor supporting Python & JS, sandboxed execution with isolation, resource limits, no network, visible & hidden test cases, autograding, large paste detection >10 lines, typing cadence analysis, MOSS-style tokenized cross-submission similarity, pre-publish test case validation).
- Phases 13–14: Interview Exam Track (Live WebRTC video room integration, question script, rubric-based panel scoring, multi-panelist independent scoring & aggregation, async interview with timed recorded responses, Whisper-class transcription, clickable timestamped highlights, screen-share detection).
Write your findings to d:\vishwa47\v47Studio\ExamSentinel\.agents\spec_miner_survey_2\survey_report.md and a self-contained handoff to d:\vishwa47\v47Studio\ExamSentinel\.agents\spec_miner_survey_2\handoff.md. Update your progress.md as you work.
When finished, send a brief completion message to your parent orchestrator.
