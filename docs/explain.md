# ExamSentinel — Extension Explainer

## 1. Code Execution Sandbox
Student code → Monaco editor → POST /api/code/submit → Redis job queue → isolated worker (gVisor/Firecracker, NOT plain Docker) → results stream via WebSocket. No network access inside sandbox. Hard timeouts and memory caps. Hidden test cases for scoring, visible for feedback. Workers are stateless and idempotent.

## 2. Code-Specific Integrity Signals
- **Large paste detection**: record paste size + diff against prior state
- **Typing cadence**: keystroke timing deltas → burstiness/uniformity score (low-weight signal only)
- **Cross-submission similarity**: MOSS-style tokenized structural comparison, post-exam batch job
- All stay "signals," never verdicts — similar code is legitimate for simple problems; typing varies by person

## 3. Live Interview Mode
WebRTC room (LiveKit/Daily) with interview question script UI, rubric scoring, multi-panelist independent scores, session recording with consent. Use WebRTC-as-a-service — don't build signaling from scratch.

## 4. Async Interview + Transcription
Candidate records timed responses → upload → Whisper transcription → time-aligned transcript with clickable highlights (pauses, filler density, proctoring event overlap). Highlights are navigation aids for reviewers.

## 5. Adaptive Testing (IRT)
2-parameter logistic model. Each question has difficulty (b) and discrimination (a). Student ability (θ) updates after each answer. Next question selected to maximize information. Cold start: seed with instructor estimates, recalibrate from data. Report ability estimates with confidence intervals, not raw scores.

## 6. Offline Resilience
Exam state mirrored to IndexedDB on every change. On disconnect: keep accepting input locally, queue sync payload. On reconnect: replay to backend with last-write-wins per question and audit entry. Never silently drop student work.

## 7. LMS/SSO Integration
LTI for roster import and grade pushback. SAML2/OAuth2 for SSO alongside existing JWT. Use LTI standard rather than bespoke integrations.

## 8. Mobile Exam Mode
Responsive mobile view with reduced monitoring signal set. Pre-exam security check honestly reports what monitoring is possible. Mobile sessions visibly tagged with different monitoring profile.

## 9. Multi-Modal Question Types
Diagram labeling (image + clickable hotspots), whiteboard (stroke-based canvas with replay), audio response (MediaRecorder + transcription). Store strokes as vector data for process replay.

## 10. Consent & Retention
Consent capture at every collection point with versioned notice text. Per-institution retention policies. Scheduled deletion/anonymization. Right-to-deletion with audit trail. Retention must be configurable per institution.

## 11. Appeals Process
Student submits appeal against any decision. Routes to distinct reviewer queue. Full audit trail. Necessary because autograder verdicts and interview panel scores need contestability.

## 12. Accessibility
Monaco editor accessibility mode must be explicitly enabled and tested. Live captioning reuses transcription pipeline. Extended-time accommodations per student. Manual audit with assistive technology required.

## 13. CI/CD, Observability, Load Testing & DR
CI gates every merge. Key alerts: sandbox queue depth, WebSocket disconnect rate, video-room join failures. Load test the thundering herd pattern. Backup only counts as verified after a tested restore drill.

## 14. Anti-Cheat Hardening
VPN/proxy: low-weight contextual signal, never auto-block. Multi-device/multi-tab: stronger signal than VPN. Screen-share detection: WebRTC track metadata. Question-leak detection: batch comparison job. All signals → reviewer, never auto-penalty.

## 15. Cost Governance
Meter sandbox-minutes, video-minutes, transcription-minutes per institution. Budget alerts at thresholds. Graduated throttling — never interrupt in-progress exams.

## 16. Notifications, Calendar, Autograder Validation
Transactional email + SMS. Calendar integration for interview scheduling. Autograder validation: run test cases against reference solution before publish; block publish on failure.
