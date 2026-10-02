import os
import smtplib
import socket
import ssl
import json
import urllib.request
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
        return os.getenv("SMTP_SENDER") or os.getenv("SMTP_USER") or "onboarding@resend.dev"

    @property
    def smtp_host(self) -> str:
        return os.getenv("SMTP_HOST", "")

    @property
    def smtp_port(self) -> int:
        try:
            return int(os.getenv("SMTP_PORT", "465"))
        except ValueError:
            return 465

    @property
    def smtp_user(self) -> str:
        return os.getenv("SMTP_USER", "")

    @property
    def smtp_pass(self) -> str:
        return os.getenv("SMTP_PASS") or os.getenv("SMTP_PASSWORD", "")

    @property
    def configured(self) -> bool:
        """Whether outbound email has been explicitly enabled and configured."""
        return self.enabled and bool(self.smtp_host or os.getenv("RESEND_API_KEY"))

    def _send_via_resend(self, to_address: str, subject: str, html_body: str, text_body: str) -> tuple[bool, str]:
        """Send email via Resend HTTPS REST API (Port 443 - Bypasses cloud host firewall port 25/465/587 blocks)."""
        api_key = os.getenv("RESEND_API_KEY", "")
        if not api_key:
            return False, "No RESEND_API_KEY configured"

        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "ExamSentinel/2.4.0"
        }
        
        # For Resend testing, public domains (like gmail.com) must send from onboarding@resend.dev
        resend_from = os.getenv("RESEND_FROM", "")
        if resend_from:
            from_email = resend_from
        elif any(domain in self.sender.lower() for domain in ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "example.com"]):
            from_email = "ExamSentinel <onboarding@resend.dev>"
        else:
            from_email = self.sender

        if not from_email.startswith("ExamSentinel") and "<" not in from_email:
            from_email = f"ExamSentinel <{from_email}>"


        payload = {
            "from": from_email,
            "to": [to_address],
            "subject": subject,
            "html": html_body,
            "text": text_body
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status in (200, 201):
                    logger.info(f"Email delivered via Resend HTTPS API to {to_address}")
                    return True, "Email sent successfully via Resend HTTPS API"
                res_body = response.read().decode("utf-8")
                return False, f"Resend API error ({response.status}): {res_body}"
        except Exception as e:
            return False, f"Resend HTTPS API failed: {str(e)}"

    def _create_ipv4_socket(self, host: str, port: int, timeout: float = 6.0) -> socket.socket:
        """Force IPv4 socket connection to prevent Errno 101 Network Unreachable on cloud hosts."""
        addr_info = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
        last_err = None
        s = None
        for family, socktype, proto, canonname, sockaddr in addr_info:
            try:
                s = socket.socket(family, socktype, proto)
                s.settimeout(timeout)
                s.connect(sockaddr)
                return s
            except Exception as err:
                last_err = err
                if s:
                    s.close()
        raise last_err or socket.error(f"Could not connect to {host}:{port} over IPv4")

    def send_email_sync(self, to_address: str, subject: str, html_body: str, text_body: str) -> tuple[bool, str]:
        if not self.enabled:
            reason = "Email delivery is disabled on the server (ENABLE_EMAILS=false in environment)."
            logger.warning(reason)
            return False, reason

        # 1. Primary check: Resend HTTPS API (Port 443 - Never blocked on Render/Heroku/AWS)
        if os.getenv("RESEND_API_KEY"):
            resend_ok, resend_msg = self._send_via_resend(to_address, subject, html_body, text_body)
            if resend_ok:
                return True, resend_msg
            logger.warning(f"Resend HTTPS API failed: {resend_msg}. Attempting SMTP fallback...")

        if not self.smtp_host:
            reason = "Email delivery enabled but no SMTP_HOST or RESEND_API_KEY configured."
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

        context = ssl.create_default_context()
        
        # Priority list: configured port first, then 465 SSL, then 587 STARTTLS
        ports_to_try = [self.smtp_port]
        for p in [465, 587]:
            if p not in ports_to_try:
                ports_to_try.append(p)

        last_error = ""

        for port in ports_to_try:
            try:
                raw_sock = self._create_ipv4_socket(self.smtp_host, port, timeout=6.0)
                if port == 465:
                    # SMTPS Implicit SSL (Port 465)
                    secure_sock = context.wrap_socket(raw_sock, server_hostname=self.smtp_host)
                    server = smtplib.SMTP_SSL(timeout=6)
                    server.sock = secure_sock
                    server._host = self.smtp_host
                    server.file = secure_sock.makefile('rb')
                    server.getwelcome()
                    if self.smtp_user and self.smtp_pass:
                        server.login(self.smtp_user, self.smtp_pass)
                    server.sendmail(self.sender, to_address, msg.as_string())
                    server.close()
                    logger.info(f"Email sent successfully to {to_address} via SSL Port 465")
                    return True, "Email sent successfully via SSL Port 465"
                else:
                    # STARTTLS (Port 587)
                    server = smtplib.SMTP(timeout=6)
                    server.sock = raw_sock
                    server._host = self.smtp_host
                    server.file = raw_sock.makefile('rb')
                    server.getwelcome()
                    server.ehlo()
                    server.starttls(context=context)
                    server.ehlo()
                    if self.smtp_user and self.smtp_pass:
                        server.login(self.smtp_user, self.smtp_pass)
                    server.sendmail(self.sender, to_address, msg.as_string())
                    server.close()
                    logger.info(f"Email sent successfully to {to_address} via Port {port}")
                    return True, f"Email sent successfully via Port {port}"
            except Exception as e:
                try:
                    if port == 465:
                        with smtplib.SMTP_SSL(self.smtp_host, 465, timeout=6, context=context) as server:
                            if self.smtp_user and self.smtp_pass:
                                server.login(self.smtp_user, self.smtp_pass)
                            server.sendmail(self.sender, to_address, msg.as_string())
                        logger.info(f"Email sent successfully to {to_address} via fallback SSL Port 465")
                        return True, "Email sent successfully via SSL Port 465"
                    else:
                        with smtplib.SMTP(self.smtp_host, port, timeout=6) as server:
                            server.ehlo()
                            server.starttls(context=context)
                            server.ehlo()
                            if self.smtp_user and self.smtp_pass:
                                server.login(self.smtp_user, self.smtp_pass)
                            server.sendmail(self.sender, to_address, msg.as_string())
                        logger.info(f"Email sent successfully to {to_address} via fallback Port {port}")
                        return True, f"Email sent successfully via Port {port}"
                except Exception as fallback_err:
                    last_error = f"Primary ({e}) / Fallback ({fallback_err})"
                    logger.warning(f"SMTP attempt on port {port} failed: {last_error}")

        reason = (
            f"SMTP Email blocked across ports {ports_to_try} ({last_error}). "
            "Render Free Tier blocks raw SMTP ports 465/587. "
            "To enable live emails on Render, add a free RESEND_API_KEY (from https://resend.com) to Render environment variables."
        )
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
