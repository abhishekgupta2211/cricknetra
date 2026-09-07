"""Password hashing (argon2) and JWT access tokens.

Adapted from the user-supplied ``security.py`` to use CricNetra's lowercase
settings names. The rest of the app only touches these four functions.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def new_otp(digits: int = 6) -> str:
    """A numeric one-time code (for mobile verification)."""
    return "".join(secrets.choice("0123456789") for _ in range(digits))


def new_token(nbytes: int = 32) -> str:
    """A URL-safe single-use token (for password-reset links)."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """SHA-256 of a short-lived token/code — we never store the raw value."""
    return hashlib.sha256(token.encode()).hexdigest()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    """Decode/verify a JWT. Raises ``jose.JWTError`` on a bad/expired token."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


__all__ = [
    "hash_password", "verify_password", "create_access_token", "decode_access_token",
    "new_otp", "new_token", "hash_token", "JWTError",
]
