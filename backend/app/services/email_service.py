import os
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
        # Awaitable wrapper for bulk sending
        success = True
        for email in to_addresses:
            result = await asyncio.to_thread(self.send_email_sync, email, subject, html_body, text_body)
            if not result:
                success = False
        return success

email_service = EmailService()
