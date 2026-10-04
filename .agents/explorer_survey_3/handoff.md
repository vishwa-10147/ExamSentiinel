# Handoff Report: Spec Mining Survey (Phases 15–20)
**Agent**: `explorer_survey_3`  
**Working Directory**: `d:\vishwa47\v47Studio\ExamSentinel\.agents\explorer_survey_3\`  
**Target Milestone**: Survey & Spec Mining for Digital Extensions, Compliance, Operations, Security, and Governance (Phases 15–20)  
**Parent Orchestrator**: `ece9073c-dea0-4960-b4b8-49f426870db1`

---

## 1. Observation

1. **Source Document Verification**:
   - Inspected `d:\vishwa47\v47Studio\ExamSentinel\ORIGINAL_REQUEST.md` (Total 588 lines, 32,985 bytes).
   - In lines 23–35 ("What's Included"), the following tracks are defined:
     - "Digital Exam Extensions: Adaptive (IRT-based) difficulty, offline-resilient exam state, LMS/SSO integration, mobile exam mode, multi-modal question types (diagram, whiteboard, audio)" (line 30).
     - "Compliance & Legal: Versioned consent capture, per-institution data retention/deletion, student appeals process, accessibility (WCAG) audits, question-bank IP handling" (line 31).
     - "Reliability & Operations: CI/CD gating, observability/alerting, exam-start load testing, backup & disaster recovery" (line 32).
     - "Anti-Cheat Hardening: VPN/proxy detection, multi-device/multi-tab detection, interview screen-share detection, question-leak detection" (line 33).
     - "Cost & Product Polish: Usage metering and budget alerts, notifications (email/SMS), calendar integration for interviews, pre-publish autograder validation" (line 34).
2. **Architecture & File Layout Directives**:
   - In lines 94–170 ("Repository Structure"), exact component paths are defined:
     - `backend/app/api/adaptive.py`, `appeals.py`, `consent.py`, `notifications.py`, `calendar_sync.py` (lines 123–127).
     - `backend/app/services/irt_service.py`, `retention_service.py`, `device_integrity_service.py`, `screen_share_detection_service.py`, `cost_metering_service.py`, `test_case_validation_service.py` (lines 132–137).
     - `backend/app/models/question_irt_params.py`, `consent_record.py`, `retention_policy.py`, `appeal_case.py`, `device_session.py`, `usage_log.py` (lines 142–147).
     - Frontend hooks: `useOfflineSync.ts`, `useDeviceFingerprint.ts` (lines 111–112).
     - Dedicated folders: `connectors/`, `compliance/` (`retention-policies/`, `consent-flows/`, `accessibility-audits/`), `.github/workflows/`, `observability/`, `load-testing/`, `infra/backup/`, `infra/disaster-recovery/` (lines 155–165).
3. **Database Tables Explicitly Mandated**:
   - Lines 201–218 enumerate:
     - Adaptive: `question_irt_params`, `student_ability_est`.
     - LMS/SSO: `lms_sync_jobs`.
     - Compliance & Legal: `consent_records`, `data_retention_policies`, `retention_deletion_jobs`, `appeal_cases`, `appeal_actions`, `accessibility_audit_logs`.
     - Security & Device Integrity: `device_sessions`, `vpn_proxy_flags`, `multi_tab_events`.
     - Cost Governance: `usage_logs`, `budget_alerts`.
     - Product/UX: `notification_logs`, `calendar_syncs`, `question_leak_reports`.
4. **Phase Plans & Rationale Directives**:
   - Lines 335–384 detail the operational requirements for Phases 15, 16, 17, 18, 19, 20.
   - Lines 427–463 explain design rationale for 2PL IRT, offline resilience, LMS/SSO, mobile mode, multi-modal questions, consent & retention, appeals, accessibility, CI/CD, anti-cheat hardening, cost governance, notifications, calendar, and autograder validation.
5. **Non-Negotiable Constraints**:
   - Lines 483–496 define strict platform invariants:
     - "No automated 'cheating' verdicts" (line 484).
     - "No inference from demographics, appearance, disability, or emotion" (line 485).
     - "No plaintext secrets, no client-side-only auth checks" (line 486).
     - "No silent overclaiming of monitoring capability" (line 487).
     - "No student work lost on disconnect" (line 488).
     - "No untracked data collection" (line 489).
     - "No silent deletion or silent retention" (line 490).
     - "No decision without an appeal path" (line 491).
     - "No VPN/device/multi-tab signal may auto-block a student" (line 492).
     - "No budget enforcement may interrupt an exam in progress" (line 493).
     - "No production deploy without CI passing" (line 494).
     - "No claim of DR readiness without a tested restore" (line 495).
6. **Acceptance Criteria**:
   - Lines 556–588 outline explicit pass/fail acceptance criteria for Adaptive & Digital Extensions, Compliance, Reliability, Security, and Cost & Polish.

---

## 2. Logic Chain

1. **IRT Adaptive Testing**:
   - *Observation*: Line 336 mandates "IRT (2-parameter logistic) ability estimation" and line 428 specifies "Each question has difficulty (b) and discrimination (a). Student ability (θ) updates after each answer. Next question selected to maximize information. Cold start: seed with instructor estimates... Report ability estimates with confidence intervals, not raw scores."
   - *Logic*: Pure MLE diverges when a student starts with all correct or all incorrect answers (cold start). Therefore, the backend estimation engine must use Maximum A Posteriori (MAP) estimation with a standard normal prior $\theta \sim \mathcal{N}(0, 1)$ or EAP numerical integration to guarantee finite convergence from item 1. Next item selection must compute Fisher Information $I_i(\hat{\theta}) = D^2 a_i^2 P_i(\hat{\theta})(1 - P_i(\hat{\theta}))$ across unadministered questions, and termination must monitor $\text{SE}(\hat{\theta}) \le 0.30$ within $[K_{\min}, K_{\max}]$ bounds.
2. **Offline Resilience & Data Integrity**:
   - *Observation*: Line 488 ("No student work lost on disconnect") and lines 343 & 431 ("Exam state mirrored to IndexedDB on every change. On disconnect: keep accepting input locally, queue sync payload. On reconnect: replay to backend with last-write-wins per question and audit entry").
   - *Logic*: The frontend cannot rely solely on in-memory state. IndexedDB must persist question drafts, answer submissions, and proctoring telemetry in a monotonic sync queue. Upon reconnect, the queue is posted to `POST /api/exam/sessions/{session_id}/sync-replay`, resolved via Last-Write-Wins based on verified client timestamps, and annotated in the audit trail. Disconnect durations $>30\text{s}$ must be transmitted to the risk engine as `NETWORK_DISCONNECT` signals without penalizing students automatically.
3. **Appeals & Governance Role Separation**:
   - *Observation*: Line 357 requires an "Appeal reviewer queue (distinct from original reviewer)" and line 491 mandates "No decision without an appeal path."
   - *Logic*: To avoid conflict of interest and guarantee procedural justice, the database schema (`appeal_cases`) and backend business logic must strictly enforce `assigned_reviewer_id != original_reviewer_id`. The appeal case must retain the complete evidentiary package (snapshots, event logs, code diffs, transcripts) alongside student justifications.
4. **Security Signals Without Auto-Blocking**:
   - *Observation*: Line 492 ("No VPN/device/multi-tab signal may auto-block a student") and line 371 ("VPN/proxy detection via IP intelligence API (low-weight risk signal, never auto-block)").
   - *Logic*: Network anomalies (VPN, proxy, multi-tab collisions) must be routed to the risk engine as weighted signals (e.g. $+10$ for VPN, $+25$ for multi-tab) and recorded in `vpn_proxy_flags` and `multi_tab_events`. The student UI must display an informational/warning toast or modal, but must NEVER abort or lock the student out of an ongoing exam session.
5. **Cost Governance Graceful Throttling**:
   - *Observation*: Line 493 ("No budget enforcement may interrupt an exam in progress") and line 380 ("Graduated throttling (never interrupt in-progress exams)").
   - *Logic*: The cost metering service must track sandbox CPU-minutes, WebRTC video-minutes, and Whisper transcription-minutes in `usage_logs`. If an institution reaches 100% of its budget, in-progress exams must proceed to completion with zero interruption. Throttling is applied strictly to new exam launches and background batch tasks.
6. **Autograder Validation Gate**:
   - *Observation*: Line 383 ("test_case_validation_service runs all test cases against reference solution before exam publishes; block publish on failure") and line 587 ("No exam type can be published with unvalidated autograder test cases").
   - *Logic*: The exam publishing endpoint `POST /api/exams/{id}/publish` must execute a synchronous or verified asynchronous validation run: executing the instructor's reference solution against all visible and hidden test cases. If any test case fails, publishing is hard-blocked with HTTP 422 and a diagnostic report is returned.

---

## 3. Caveats

1. **Third-Party API Secrets**: Actual integration with live third-party services (LiveKit cloud, Daily.co, AWS SES, Twilio, Google Calendar API, MS Graph API, IP intelligence APIs) requires institution-specific credentials and environment variables. The architecture is designed with modular interfaces and local/mock fallbacks (e.g., local iCal `.ics` generation, local mock IP intelligence, SMTP/console email fallbacks) for offline development and testing.
2. **IRT Parameter Recalibration Dataset Scale**: Accurate item parameter recalibration ($a_i, b_i$) via Marginal Maximum Likelihood Estimation (MMLE) requires sample sizes of $N \ge 200$ student responses per item. In initial development and testing, seeded parameters ($a=1.0, b \in [-2, 2]$) are utilized.
3. **Execution Sandbox Isolation in Development**: While production mandates gVisor or Firecracker virtualization, local Docker Compose environments simulate sandbox limits using Docker container resource flags (`--cpus`, `--memory`, `--network none`).

---

## 4. Conclusion

All specifications, mathematical formulations, database schemas (23 distinct tables), API endpoints (28 distinct routes), operational parameters, and non-negotiable constraints for **Phases 15 through 20** have been mined and fully documented in:
- `d:\vishwa47\v47Studio\ExamSentinel\.agents\explorer_survey_3\survey_report.md`

The system design enforces:
- Psychometrically valid 2PL IRT adaptive testing with Bayesian MAP ability estimation and Fisher information selection.
- Multi-modal question types (diagram labeling, stroke-replay whiteboard, audio response with time-aligned Whisper transcripts).
- Zero data-loss offline resilience via IndexedDB sync queue and replay.
- Enterprise integration via standard 1EdTech LTI 1.3 (OIDC/NRPS/AGS) and SAML2/OAuth2 SSO.
- Transparent mobile examination with explicit capability disclosure.
- Legally sound compliance through versioned consent, automated retention/deletion, and independent appeals.
- Resilient operations via GitHub Actions CI gating, structlog distributed tracing, Prometheus alerting, k6 load testing, and verified DR restore drills.
- Human-in-the-loop security hardening (VPN, multi-device, screen-share, question-leak) that never auto-blocks students.
- Strict cost governance with non-interruptive budget enforcement and pre-publish autograder validation gates.

---

## 5. Verification Method

To independently verify the accuracy and completeness of this report:
1. **File Inspection**:
   - Inspect `d:\vishwa47\v47Studio\ExamSentinel\.agents\explorer_survey_3\survey_report.md` and confirm it addresses every bullet in `d:\vishwa47\v47Studio\ExamSentinel\.agents\explorer_survey_3\DISPATCH.md`.
   - Cross-check table names in `survey_report.md` Section 8 against `ORIGINAL_REQUEST.md` lines 201–218.
   - Cross-check invariant constraints in `survey_report.md` Section 10 against `ORIGINAL_REQUEST.md` lines 483–496.
2. **Formula Validation**:
   - Verify the 2PL IRT probability formula $P_i(\theta) = \frac{1}{1 + e^{-D a_i (\theta - b_i)}}$ with $D=1.702$, the log-likelihood derivative $\ell'(\theta) = D \sum a_i (u_i - P_i)$, and Fisher information $I_i(\theta) = D^2 a_i^2 P_i (1 - P_i)$.
3. **Downstream Subagent Verification**:
   - Milestone sub-orchestrators and workers can directly consume `survey_report.md` to implement database models, migrations, service algorithms, and API endpoints without missing any constraints or edge cases.
