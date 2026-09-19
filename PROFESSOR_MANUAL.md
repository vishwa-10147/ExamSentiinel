# ExamSentinel: Professor & Administration Manual

Welcome to ExamSentinel. This guide will teach you how to manage your examinations, monitor students in real-time, and utilize the AI Assistant for grading.

## 1. Creating and Managing Exams

### Uploading Question Banks
Instead of manually typing every question, you can bulk upload them using a CSV file.
1. Navigate to the **Exam Management** page for your specific exam.
2. Under the **Question Bank** section, click **Upload Paper (CSV)**.
3. Your CSV must have the following headers: `title`, `type` (e.g., `MCQ_SINGLE`, `CODING`, `SQL`, `ESSAY`), `content`, `points`, `difficulty`.

### Registering Students
1. Go to the **Users** tab on the sidebar.
2. Click **Bulk Import**.
3. Upload a CSV roster containing `email`, `full_name`, and `roll_number`.
4. The system will automatically create accounts for your students and group them by Roll Number batch. (If AWS SES is enabled by IT, students will immediately receive an email with their login credentials).

## 2. Live Exam Monitoring & Proctoring

When an exam is active, you can monitor students in real time via the **Live Monitoring** dashboard.

### The Risk Engine
ExamSentinel assigns every student a live **Risk Score** (Low, Medium, High, Critical) based on proctoring events:
- **Browser Events**: Tab switching, copy/paste attempts, exiting full-screen mode.
- **Webcam Events**: No face detected, multiple faces detected, or phones detected.
- **Network & Device**: Multi-device logins or unexpected VPN usage.

*Note: You can override the default weights for these events in the Settings panel.*

### Plagiarism Detection
After an exam completes, the system runs a deep **Code Similarity Analysis**.
It intelligently strips out comments and whitespace, comparing the logical sequences of code between all students to catch identical logic structures. Flagged students will be marked in red on the grading dashboard.

## 3. The AI Grading Assistant

We have integrated an AI Pre-Grading Assistant (Powered by Gemini 2.0) to save you hours of manual review.

### How to use it:
1. Navigate to the **Professor Grading Dashboard** for a completed exam.
2. Select a student's submission.
3. Click the **✨ Auto-Grade** button.
4. The AI will evaluate the student's code/essay against the maximum points and your specific rubric. 
5. It will pre-fill the **Marks** field and provide an explanation in the **Feedback** box.
6. **Important:** The AI is an *assistant*. You should always briefly review its suggestion and hit **Save Grade** to finalize it.

## 4. Compliance & Exporting Grades

Once all exams are graded:
1. Navigate to the Exam Management page.
2. Click **Export Grades (CSV)**.
3. This downloads an official Registrar-compliant file containing Student Names, Roll Numbers, Risk Scores, and Final Grades.
