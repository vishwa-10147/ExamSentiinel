import boto3
from botocore.exceptions import ClientError
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.sender = os.getenv("SES_SENDER_EMAIL", "noreply@exams.myuniversity.edu")
        
        # If running on EC2/ECS, boto3 automatically uses the IAM instance profile.
        # Otherwise, it uses AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY from env.
        try:
            self.client = boto3.client('ses', region_name=self.region)
            self.enabled = os.getenv("ENABLE_EMAILS", "false").lower() == "true"
        except Exception as e:
            logger.warning(f"Failed to initialize SES client: {e}")
            self.client = None
            self.enabled = False

    def send_email(self, to_address: str, subject: str, html_body: str, text_body: str) -> bool:
        if not self.enabled or not self.client:
            logger.info(f"[EMAIL MOCK] To: {to_address} | Subject: {subject}")
            logger.debug(f"Body: {text_body}")
            return True

        try:
            response = self.client.send_email(
                Destination={
                    'ToAddresses': [to_address],
                },
                Message={
                    'Body': {
                        'Html': {'Charset': "UTF-8", 'Data': html_body},
                        'Text': {'Charset': "UTF-8", 'Data': text_body},
                    },
                    'Subject': {'Charset': "UTF-8", 'Data': subject},
                },
                Source=self.sender,
            )
            logger.info(f"Email sent! Message ID: {response['MessageId']}")
            return True
        except ClientError as e:
            logger.error(f"SES Email failed: {e.response['Error']['Message']}")
            return False

    def send_welcome_email(self, to_address: str, name: str, temp_password: str):
        subject = "Welcome to ExamSentinel"
        text = f"Hello {name},\\n\\nYour account has been created.\\nPassword: {temp_password}\\n\\nPlease log in and change it."
        html = f"<p>Hello {name},</p><p>Your account has been created.</p><p>Password: <strong>{temp_password}</strong></p>"
        self.send_email(to_address, subject, html, text)

    def send_grade_published_email(self, to_address: str, name: str, exam_title: str):
        subject = f"Grades Published: {exam_title}"
        text = f"Hello {name},\\n\\nYour grades for {exam_title} have been published. Log in to view your results."
        html = f"<p>Hello {name},</p><p>Your grades for <strong>{exam_title}</strong> have been published.</p>"
        self.send_email(to_address, subject, html, text)

email_service = EmailService()
