"""Pluggable OTP / notification delivery.

Verification codes and password-reset codes are sent through a `Notifier`. The
default backend just logs (so the flow is fully testable with no provider); set
the Twilio env vars to send real SMS, or the SMTP vars to send real email. A
delivery failure never breaks the request — it's logged and swallowed (the code
is still issued; the user can retry).
"""

from __future__ import annotations

import logging
from typing import Optional, Protocol

from app.core.config import settings

logger = logging.getLogger("cricnetra.notify")


class SmsBackend(Protocol):
    def sms(self, to: str, message: str) -> None: ...


class EmailBackend(Protocol):
    def email(self, to: str, subject: str, body: str) -> None: ...


class ConsoleSender:
    """Dev default — logs the message instead of sending it."""

    def sms(self, to: str, message: str) -> None:
        logger.info("[console-sms] to=%s :: %s", to, message)

    def email(self, to: str, subject: str, body: str) -> None:
        logger.info("[console-email] to=%s subject=%r :: %s", to, subject, body)


class TwilioSmsBackend:
    """Send SMS via Twilio's REST API (uses httpx, already a dependency)."""

    def __init__(self, sid: str, token: str, sender: str) -> None:
        self.sid, self.token, self.sender = sid, token, sender

    def sms(self, to: str, message: str) -> None:
        import httpx

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.sid}/Messages.json"
        resp = httpx.post(
            url, auth=(self.sid, self.token),
            data={"From": self.sender, "To": to, "Body": message}, timeout=10,
        )
        resp.raise_for_status()


class SmtpEmailBackend:
    """Send email via SMTP (stdlib smtplib)."""

    def __init__(self, host: str, port: int, user: Optional[str],
                 password: Optional[str], sender: str, starttls: bool) -> None:
        self.host, self.port, self.user = host, port, user
        self.password, self.sender, self.starttls = password, sender, starttls

    def email(self, to: str, subject: str, body: str) -> None:
        import smtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = self.sender, to, subject
        msg.set_content(body)
        with smtplib.SMTP(self.host, self.port, timeout=10) as srv:
            if self.starttls:
                srv.starttls()
            if self.user:
                srv.login(self.user, self.password or "")
            srv.send_message(msg)


class Notifier:
    """Facade over an SMS + an email backend; never raises on delivery failure."""

    def __init__(self, sms_backend: Optional[SmsBackend] = None,
                 email_backend: Optional[EmailBackend] = None) -> None:
        self.sms_backend = sms_backend or ConsoleSender()
        self.email_backend = email_backend or ConsoleSender()

    def send_sms(self, to: str, message: str) -> None:
        try:
            self.sms_backend.sms(to, message)
        except Exception as e:  # pragma: no cover - provider/network failures
            logger.warning("SMS delivery failed (to=%s): %s", to, e)

    def send_email(self, to: str, subject: str, body: str) -> None:
        try:
            self.email_backend.email(to, subject, body)
        except Exception as e:  # pragma: no cover - provider/network failures
            logger.warning("email delivery failed (to=%s): %s", to, e)


def build_notifier() -> Notifier:
    """Construct a Notifier from settings — Twilio/SMTP when configured, else console."""
    console = ConsoleSender()
    sms: SmsBackend = console
    email: EmailBackend = console
    if settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_from:
        sms = TwilioSmsBackend(settings.twilio_account_sid, settings.twilio_auth_token, settings.twilio_from)
    if settings.smtp_host:
        email = SmtpEmailBackend(
            settings.smtp_host, settings.smtp_port, settings.smtp_user,
            settings.smtp_password, settings.smtp_from or settings.smtp_user or "no-reply@cricnetra",
            settings.smtp_starttls,
        )
    return Notifier(sms, email)
