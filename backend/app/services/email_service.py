import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.models.user import UserRole
import asyncio

class EmailService:
    def __init__(self):
        self.host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.user = os.getenv("SMTP_USER", "")
        self.password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("EMAIL_FROM_ADDRESS", "noreply@examsentinel.edu")

    def _send_sync(self, to: list[str], subject: str, html_body: str):
        if not self.user or not self.password:
            # Mock sending if not configured
            print(f"MOCK EMAIL to {to}: {subject}")
            return True
            
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = ", ".join(to)
            msg.attach(MIMEText(html_body, "html"))

            server = smtplib.SMTP(self.host, self.port)
            server.starttls()
            server.login(self.user, self.password)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            print(f"Email failed: {e}")
            return False

    async def send(self, to: list[str], subject: str, html_body: str):
        return await asyncio.to_thread(self._send_sync, to, subject, html_body)

email_service = EmailService()
