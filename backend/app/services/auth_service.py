"""AuthService — register & login, on top of the user repository.

Adapted from the user-supplied ``auth_service.py``: data access goes through the
repository (not a raw Session), and it raises a domain ``AuthError`` that the
route maps to an HTTP status — fixing the original ``HTTPException("...")`` and
``if not User.is_active`` (class-vs-instance) bugs along the way.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.permissions import DEFAULT_SIGNUP_ROLE, Roles
from app.core.security import (
    create_access_token,
    hash_password,
    hash_token,
    new_token,
    verify_password,
)
from app.repositories.auth_token_repository import AuthTokenRepository
from app.repositories.role_request_repository import RoleRequestRepository
from app.repositories.user_repository import UserRecord, UserRepository
from app.schemas.auth import UserLogin, UserSignup


class AuthError(Exception):
    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class AuthService:
    def __init__(
        self,
        repo: UserRepository,
        role_requests: RoleRequestRepository | None = None,
        tokens: AuthTokenRepository | None = None,
    ) -> None:
        self.repo = repo
        self.role_requests = role_requests
        self.tokens = tokens

    def register(self, payload: UserSignup) -> UserRecord:
        """Create an account. Everyone starts as a general user.

        A role is something an admin grants after looking at the person, not
        something a stranger picks for themselves — otherwise anyone could sign
        up as an organizer and start running competitions. If they said what
        they are at sign-up, that is recorded as a request for an admin to act
        on; it never sets the role.
        """
        if self.repo.get_by_mobile(payload.mobile_no) is not None:
            raise AuthError("Mobile number already registered", 409)
        if self.repo.get_by_username(payload.username) is not None:
            raise AuthError("Username already taken", 409)

        user = self.repo.add_user(
            full_name=payload.full_name.strip(),
            username=payload.username,
            mobile_no=payload.mobile_no,
            password_hash=hash_password(payload.password),
            role=DEFAULT_SIGNUP_ROLE,
            email=payload.email,
        )
        wanted = (payload.role or "").strip().lower()
        if (
            wanted
            and wanted not in (DEFAULT_SIGNUP_ROLE, Roles.ADMIN)
            and self.role_requests is not None
        ):
            self.role_requests.add(user.id, wanted)
        return user

    def login(self, payload: UserLogin) -> dict:
        user = self.repo.get_by_identifier(payload.identifier)
        # One generic message whether the user is missing or the password is
        # wrong, so we don't leak which usernames/numbers exist.
        if user is None or not verify_password(payload.password, user.password):
            raise AuthError("Invalid credentials", 401)
        if not user.is_active:
            raise AuthError("Account is inactive", 403)
        return self._issue(user)

    def _issue(self, user: UserRecord) -> dict:
        """Mint a fresh short-lived access token + a stored, revocable refresh token."""
        access = create_access_token({
            "sub": user.id, "role": user.role,
            "user_code": user.user_code, "role_code": user.role_code,
        })
        refresh = new_token()
        if self.tokens is not None:
            ttl = timedelta(days=settings.refresh_token_expire_days)
            self.tokens.add(user.id, "refresh", hash_token(refresh), datetime.now(timezone.utc) + ttl)
        return {"access_token": access, "token_type": "bearer", "refresh_token": refresh}

    def refresh(self, refresh_token: str) -> dict:
        if self.tokens is None:
            raise AuthError("Refresh is unavailable", 400)
        tok = self.tokens.find_valid("refresh", hash_token(refresh_token.strip()))
        if tok is None:
            raise AuthError("Session expired — please sign in again", 401)
        user = self.repo.get_by_id(tok.user_id)
        if user is None or not user.is_active:
            raise AuthError("Account is unavailable", 401)
        self.tokens.mark_used(tok.id)  # rotate: the old refresh token is now spent
        return self._issue(user)

    def logout(self, refresh_token: str) -> None:
        if self.tokens is None:
            return
        tok = self.tokens.find_valid("refresh", hash_token(refresh_token.strip()))
        if tok is not None:
            self.tokens.mark_used(tok.id)

    def logout_all(self, user_id: str) -> None:
        """Sign a user out everywhere: revoke every outstanding refresh token.

        Access tokens are stateless and expire on their own (minutes); killing the
        refresh tokens means no session can be renewed past that."""
        if self.tokens is not None:
            self.tokens.invalidate(str(user_id), "refresh")
