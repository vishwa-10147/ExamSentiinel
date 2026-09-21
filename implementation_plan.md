# ExamSentinel Production Readiness: Phase 2

This plan implements three critical modules for institutional production readiness, plus the new UI/Sandbox enhancements you requested:

## Proposed Changes

### 1. Navigation Bar Toggle (Hamburger Menu)
**Frontend:**
- [NEW] rontend/contexts/SidebarContext.tsx: Create a global state context for isSidebarOpen.
- [MODIFY] rontend/app/layout.tsx: Wrap the app in <SidebarProvider>.
- [MODIFY] rontend/components/Navbar.tsx: Add a 3-lines (Hamburger) button on the left that toggles isSidebarOpen.
- [MODIFY] rontend/components/Sidebar.tsx: Update Tailwind classes to slide in/out based on isSidebarOpen (e.g., transform -translate-x-full on mobile, or completely collapse width on desktop).

### 2. LeetCode-Style Professional Code Sandbox
**Frontend:**
- [MODIFY] rontend/app/candidate/practice/page.tsx:
  - Upgrade the UI to a robust Split-Pane layout (using standard Flexbox or a resizable panel library if available).
  - Fix the hardcoded http://localhost:8000 API call to use the dynamic NEXT_PUBLIC_API_URL so it actually connects to the production execution cluster.
  - Enhance the terminal output pane with better ANSI color parsing and LeetCode-style success/failure states.
- **Backend Note**: The backend SandboxService is already built! It supports Python, JavaScript, Java, C++, C, Go, Rust, and SQL via isolated Docker containers. The frontend will now correctly route to it.

### 3. CSV Bulk Import for Questions
**Frontend & Backend:**
- [MODIFY] rontend/app/admin/questions/page.tsx: Add an "Import from CSV" modal.
- [MODIFY] ackend/app/api/questions.py: Add an endpoint POST /api/questions/bulk to parse CSVs and perform a bulk insert into the database.

### 4. SMTP Email Configuration
**Backend:**
- [MODIFY] ackend/app/services/email_service.py: Rewrite to support standard SMTP (smtplib) as the primary driver, alongside the existing AWS SES integration.
- [MODIFY] ackend/app/api/broadcast.py: Fix the currently broken email_service.send() method call so emails dispatch successfully asynchronously.

### 5. S3 Storage for Proctoring Snapshots
**Backend & Frontend:**
- [NEW] ackend/app/services/storage_service.py: A wrapper around oto3 to upload images to an AWS S3 bucket.
- [MODIFY] ackend/app/api/proctoring.py: Add an endpoint POST /api/proctoring/evidence/{session_id}.
- [MODIFY] rontend/components/FaceTracker.tsx: Auto-capture frames on violation and POST to the evidence endpoint.

## Verification Plan
1. Click the hamburger menu in the Navbar to ensure the Sidebar cleanly slides in/out.
2. Run a Python/C++ script in the Code Sandbox and verify the output returns from the actual Render backend without CORS or localhost errors.
3. Upload a sample CSV, send a test email broadcast, and trigger a FaceTracker violation to verify storage.
