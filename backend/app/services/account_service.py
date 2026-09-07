"""Account verification (mobile OTP) + password reset.

Tokens are single-use and short-lived; only their hash is stored. Delivery is
abstracted: today the code/token is returned to the route (dev delivery) and
logged; swapping in a real SMS/email sender is a one-line change at the route.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.core.config import settings
from app.core.notifications import Notifier, build_notifier
from app.core.security import hash_password, hash_token, new_otp, new_token
from app.repositories.auth_token_repository import AuthTokenRepository
from app.repositories.user_repository import UserRecord, UserRepository

logger = logging.getLogger(__name__)

_APP = "CricNetra"


class AccountError(Exception):
    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AccountService:
    def __init__(self, users: UserRepository, tokens: AuthTokenRepository,
                 notifier: Optional[Notifier] = None) -> None:
        self.users = users
        self.tokens = tokens
        self.notifier = notifier or build_notifier()

    def _deliver(self, user: UserRecord, subject: str, message: str) -> None:
        """Send a code to the user — by email when we have one (free tier path),
        otherwise by SMS. Either backend no-ops to a log if unconfigured."""
        if user.email:
            self.notifier.send_email(user.email, subject, message)
        else:
            self.notifier.send_sms(user.mobile_no, message)

    # ----- account verification (email when on file, else SMS) -----
    def request_verification(self, user: UserRecord) -> Optional[str]:
        """Issue a fresh verification code and deliver it. Returns the raw code
        (the route decides whether to also expose it); None if already verified."""
        if user.is_verified:
            return None
        self.tokens.invalidate(user.id, "verify")
        code = new_otp(6)
        ttl = settings.verify_code_ttl_minutes
        self.tokens.add(user.id, "verify", hash_token(code), _now() + timedelta(minutes=ttl))
        self._deliver(
            user, f"{_APP} verification code",
            f"{_APP}: your verification code is {code}. It expires in {ttl} minutes.",
        )
        return code

    def confirm_verification(self, user: UserRecord, code: str) -> None:
        tok = self.tokens.find_valid("verify", hash_token(code.strip()), user_id=user.id)
        if tok is None:
            raise AccountError("That code is invalid or has expired.")
        self.tokens.mark_used(tok.id)
        self.users.set_verified(user.id, True)

    # ----- password reset -----
    def request_reset(self, identifier: str) -> Optional[str]:
        """Issue a reset token for the user matching the identifier, or None if no
        such user (the route always reports generic success, to avoid leaking)."""
        ident = identifier.strip()
        user = self.users.get_by_identifier(ident)
        if user is None and "@" in ident:  # let people reset by their email too
            user = self.users.get_by_email(ident)
        if user is None:
            return None
        self.tokens.invalidate(user.id, "reset")
        token = new_token()
        ttl = settings.reset_token_ttl_minutes
        self.tokens.add(user.id, "reset", hash_token(token), _now() + timedelta(minutes=ttl))
        self._deliver(
            user, f"{_APP} password reset",
            f"{_APP}: your password reset code is {token} (expires in {ttl} min). "
            f"Ignore this if you didn't request it.",
        )
        return token

    def reset_password(self, token: str, new_password: str) -> None:
        tok = self.tokens.find_valid("reset", hash_token(token.strip()))
        if tok is None:
            raise AccountError("This reset link is invalid or has expired.")
        self.tokens.mark_used(tok.id)
        self.users.set_password(tok.user_id, hash_password(new_password))
