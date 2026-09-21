import os

# 5. Email Service
with open("backend/app/services/email_service.py", "w", encoding="utf-8") as f:
    f.write('''import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
from app.core.logging import logger

class EmailService:
    def __init__(self):
        self.enabled = os.getenv("ENABLE_EMAILS", "false").lower() == "true"
        self.sender = os.getenv("SMTP_SENDER", "noreply@exams.myuniversity.edu")
        self.smtp_host = os.getenv("SMTP_HOST", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_pass = os.getenv("SMTP_PASS", "")

    def send_email_sync(self, to_address: str, subject: str, html_body: str, text_body: str) -> bool:
        if not self.enabled:
            logger.info(f"[EMAIL MOCK] To: {to_address} | Subject: {subject}")
            return True

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.sender
        msg['To'] = to_address

        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        msg.attach(part1)
        msg.attach(part2)

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                if self.smtp_user and self.smtp_pass:
                    server.login(self.smtp_user, self.smtp_pass)
                server.sendmail(self.sender, to_address, msg.as_string())
            logger.info(f"Email sent successfully to {to_address}")
            return True
        except Exception as e:
            logger.error(f"SMTP Email failed: {str(e)}")
            return False

    async def send(self, to_addresses: list[str], subject: str, html_body: str, text_body: str = "") -> bool:
        success = True
        for email in to_addresses:
            result = await asyncio.to_thread(self.send_email_sync, email, subject, html_body, text_body)
            if not result:
                success = False
        return success

email_service = EmailService()
''')

# 6. Storage Service
with open("backend/app/services/storage_service.py", "w", encoding="utf-8") as f:
    f.write('''import os
import uuid
import base64
import boto3
from botocore.exceptions import ClientError
from app.core.logging import logger

class StorageService:
    def __init__(self):
        self.bucket = os.getenv("AWS_BUCKET_NAME", "")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.enabled = bool(self.bucket)
        if self.enabled:
            self.s3_client = boto3.client('s3', region_name=self.region)
        else:
            self.s3_client = None

    def upload_base64_image(self, base64_str: str, prefix: str = "evidence") -> str:
        if not self.enabled:
            return "https://mock-storage.local/evidence.jpg"

        try:
            if "," in base64_str:
                base64_str = base64_str.split(",")[1]
            image_data = base64.b64decode(base64_str)
            filename = f"{prefix}/{uuid.uuid4().hex}.jpg"
            self.s3_client.put_object(Bucket=self.bucket, Key=filename, Body=image_data, ContentType='image/jpeg')
            return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{filename}"
        except Exception as e:
            return ""

storage_service = StorageService()
''')

# 7. Sandbox Service
with open("backend/app/services/sandbox_service.py", "w", encoding="utf-8") as f:
    f.write('''import httpx
import time
from dataclasses import dataclass
from app.core.logging import logger

@dataclass
class SandboxResult:
    status: str
    stdout: str
    stderr: str
    exit_code: int | None
    wall_time_ms: int

class SandboxService:
    def __init__(self) -> None:
        self.piston_url = "https://emkc.org/api/v2/piston/execute"
        self.language_map = {
            "python": {"language": "python", "version": "3.10.0"},
            "javascript": {"language": "javascript", "version": "18.15.0"},
            "java": {"language": "java", "version": "15.0.2"},
            "c++": {"language": "c++", "version": "10.2.0"},
            "cpp": {"language": "c++", "version": "10.2.0"},
        }

    async def execute_async(self, language: str, source_code: str, stdin: str, timeout_sec: float, memory_mb: int) -> SandboxResult:
        if language not in self.language_map:
            raise ValueError(f"Unsupported language: {language}")

        lang_config = self.language_map[language]
        
        payload = {
            "language": lang_config["language"],
            "version": lang_config["version"],
            "files": [{"name": f"main.{language}", "content": source_code}],
            "stdin": stdin,
            "compile_timeout": int(timeout_sec * 1000),
            "run_timeout": int(timeout_sec * 1000),
        }
        
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=timeout_sec + 2.0) as client:
                response = await client.post(self.piston_url, json=payload)
                response.raise_for_status()
                data = response.json()
                
                wall_time_ms = int((time.perf_counter() - started) * 1000)
                run_data = data.get("run", {})
                compile_data = data.get("compile", {})
                
                stderr = run_data.get("stderr", "")
                if compile_data.get("stderr"):
                    stderr = compile_data["stderr"] + "\\n" + stderr
                    
                stdout = run_data.get("stdout", "")
                exit_code = run_data.get("code", compile_data.get("code", 1))
                
                status = "success" if exit_code == 0 else "error"
                return SandboxResult(status=status, stdout=stdout, stderr=stderr, exit_code=exit_code, wall_time_ms=wall_time_ms)
                
        except Exception as e:
            return SandboxResult(status="system_error", stdout="", stderr=str(e), exit_code=-1, wall_time_ms=0)

sandbox_service = SandboxService()
''')

# 8. Update APIs
with open("backend/app/api/code_execution.py", "r", encoding="utf-8") as f:
    ce = f.read()
ce = ce.replace('sandbox_service.execute(', 'await sandbox_service.execute_async(')
ce = ce.replace('from app.services.sandbox_service import SandboxUnavailableError, sandbox_service', 'from app.services.sandbox_service import sandbox_service')
with open("backend/app/api/code_execution.py", "w", encoding="utf-8") as f:
    f.write(ce)

with open("backend/app/api/proctoring.py", "r", encoding="utf-8") as f:
    proc = f.read()
proc = proc.replace('from pydantic import', 'from pydantic import BaseModel,')
proc = proc.replace("from app.services.risk_engine import risk_engine", "from app.services.storage_service import storage_service\\nfrom app.services.risk_engine import risk_engine")
proc += '''
class EvidenceRequest(BaseModel):
    image_base64: str
    event_type: str
    metadata: Optional[dict] = None

@router.post("/evidence/{session_id}")
async def upload_evidence(session_id: uuid.UUID, payload: EvidenceRequest, db: AsyncSession = Depends(get_db)):
    import asyncio
    image_url = await asyncio.to_thread(storage_service.upload_base64_image, payload.image_base64, f"evidence/{session_id}")
    return {"status": "success", "image_url": image_url}
'''
with open("backend/app/api/proctoring.py", "w", encoding="utf-8") as f:
    f.write(proc)

with open("backend/app/api/questions.py", "r", encoding="utf-8") as f:
    ques = f.read()
ques = ques.replace('from fastapi import APIRouter', 'from fastapi import APIRouter, UploadFile, File\\nimport csv\\nimport io')
ques += '''
@router.post("/bulk")
async def bulk_upload_questions(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    contents = await file.read()
    try: text = contents.decode('utf-8')
    except UnicodeDecodeError: raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded.")
    reader = csv.DictReader(io.StringIO(text))
    questions_to_insert = []
    for row in reader:
        try:
            q = Question(id=uuid.uuid4(), title=row.get('title', '').strip(), content=row.get('content', '').strip(), type=QuestionType(row.get('type', 'multiple_choice')), difficulty=QuestionDifficulty(row.get('difficulty', 'medium')), points=int(row.get('points', 10)), options=row.get('options', '').split('|') if row.get('options') else [], correct_answer=row.get('correct_answer', '').strip())
            questions_to_insert.append(q)
        except: pass
    if not questions_to_insert: raise HTTPException(status_code=400, detail="No valid questions found in CSV.")
    db.add_all(questions_to_insert)
    await db.commit()
    return {"status": "success", "inserted": len(questions_to_insert)}
'''
with open("backend/app/api/questions.py", "w", encoding="utf-8") as f:
    f.write(ques)

print("Backend complete")
