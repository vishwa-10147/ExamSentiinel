import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
from app.core.logging import logger

class EmailService:
    @property
    def enabled(self) -> bool:
        return os.getenv("ENABLE_EMAILS", "false").lower() == "true"

    @property
    def sender(self) -> str:
        return os.getenv("SMTP_SENDER") or os.getenv("SMTP_USER") or "noreply@examsentinel.edu"

    @property
    def smtp_host(self) -> str:
        return os.getenv("SMTP_HOST", "")

    @property
    def smtp_port(self) -> int:
        try:
            return int(os.getenv("SMTP_PORT", "587"))
        except ValueError:
            return 587

    @property
    def smtp_user(self) -> str:
        return os.getenv("SMTP_USER", "")

    @property
    def smtp_pass(self) -> str:
        return os.getenv("SMTP_PASS") or os.getenv("SMTP_PASSWORD", "")

    @property
    def configured(self) -> bool:
        """Whether outbound email has been explicitly enabled and configured."""
        return self.enabled and bool(self.smtp_host and self.sender)

    def send_email_sync(self, to_address: str, subject: str, html_body: str, text_body: str) -> tuple[bool, str]:
        if not self.enabled:
            reason = "Email delivery is disabled on the server (ENABLE_EMAILS=false in environment)."
            logger.warning(reason)
            return False, reason
        if not self.smtp_host:
            reason = "Email delivery is enabled but SMTP_HOST is not configured in server environment."
            logger.error(reason)
            return False, reason

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.sender
        msg['To'] = to_address

        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        msg.attach(part1)
        msg.attach(part2)

        import socket
        import ssl

        target_host = self.smtp_host
        try:
            addr_info = socket.getaddrinfo(self.smtp_host, self.smtp_port, socket.AF_INET, socket.SOCK_STREAM)
            if addr_info:
                target_host = addr_info[0][4][0]
        except Exception as resolve_err:
            logger.warning(f"IPv4 resolution fallback warning: {resolve_err}")

        # List of ports to attempt: configured port first, followed by port 465 SSL fallback
        ports_to_try = [self.smtp_port]
        if 465 not in ports_to_try:
            ports_to_try.append(465)

        last_error = ""
        context = ssl.create_default_context()

        for port in ports_to_try:
            try:
                if port == 465:
                    # SMTPS (Implicit SSL over Port 465) - bypasses STARTTLS firewall blocks on cloud hosts
                    with smtplib.SMTP_SSL(target_host, 465, timeout=8, context=context) as server:
                        server._host = self.smtp_host
                        if self.smtp_user and self.smtp_pass:
                            server.login(self.smtp_user, self.smtp_pass)
                        server.sendmail(self.sender, to_address, msg.as_string())
                    logger.info(f"Email sent successfully to {to_address} via SSL Port 465")
                    return True, "Email sent successfully via SSL Port 465"
                else:
                    # Standard STARTTLS over Port 587
                    with smtplib.SMTP(timeout=8) as server:
                        server.connect(target_host, port)
                        server._host = self.smtp_host
                        server.ehlo()
                        server.starttls(context=context)
                        server.ehlo()
                        if self.smtp_user and self.smtp_pass:
                            server.login(self.smtp_user, self.smtp_pass)
                        server.sendmail(self.sender, to_address, msg.as_string())
                    logger.info(f"Email sent successfully to {to_address} via Port {port}")
                    return True, f"Email sent successfully via Port {port}"
            except Exception as e:
                last_error = str(e)
                logger.warning(f"SMTP attempt on port {port} failed: {last_error}. Trying fallback...")

        reason = f"SMTP Email failed across ports {ports_to_try}: {last_error}"
        logger.error(reason)
        return False, reason



    async def send(self, to_addresses: list[str], subject: str, html_body: str, text_body: str = "") -> bool:
        success, _ = await self.send_with_reason(to_addresses, subject, html_body, text_body)
        return success

    async def send_with_reason(self, to_addresses: list[str], subject: str, html_body: str, text_body: str = "") -> tuple[bool, str]:
        success = True
        last_reason = ""
        for email in to_addresses:
            result, reason = await asyncio.to_thread(self.send_email_sync, email, subject, html_body, text_body)
            if not result:
                success = False
                last_reason = reason
        return success, last_reason

email_service = EmailService()

