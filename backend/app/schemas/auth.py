"""Auth request/response schemas (from the user-supplied ``auth.py``)."""

from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

ALLOWED_ROLES = {
    "player",
    "umpire",
    "commentator",
    "organizer",
    "team_owner",
    "admin",
    "general_user",
}


class UserSignup(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    username: str = Field(..., min_length=3, max_length=50)
    mobile_no: str = Field(..., min_length=10, max_length=20)
    # Optional on the API (back-compat + tests); the signup form collects it and
    # it's used as the OTP / password-reset delivery address (free email path).
    email: Optional[str] = Field(default=None, max_length=255)
    password: str = Field(..., min_length=6, max_length=100)
    # Every account is created as a general user. This field is kept for
    # existing clients and for the sign-up form's "I am a…" question: it is
    # recorded as a request for an admin to consider, and never sets the role.
    role: Optional[str] = Field(default=None, min_length=3, max_length=50)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip().lower()
        if not value:
            return None
        if "@" not in value or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address")
        return value

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip().lower()
        if value not in ALLOWED_ROLES:
            raise ValueError(
                "Invalid role. Allowed roles are: "
                + ", ".join(sorted(ALLOWED_ROLES))
            )
        return value

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("mobile_no")
    @classmethod
    def validate_mobile_no(cls, value: str) -> str:
        # accept common formats — "+91 95922-42452", "(044) 1234..." — by keeping
        # only the digits, then check it's a sensible 10–15 digit number.
        digits = re.sub(r"\D", "", value or "")
        if not (10 <= len(digits) <= 15):
            raise ValueError("Enter a valid mobile number (10–15 digits)")
        return digits


class UserLogin(BaseModel):
    identifier: str = Field(..., min_length=3, max_length=50)  # username or mobile
    password: str = Field(..., min_length=6, max_length=100)

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        value = value.strip()
        compact = re.sub(r"[\s\-()+]", "", value)  # strip phone formatting
        if compact.isdigit():  # a mobile number — normalise to digits (matches sign-up)
            if not (10 <= len(compact) <= 15):  # was `value != 10` — a bug
                raise ValueError("Enter a valid mobile number (10–15 digits)")
            return compact
        if not value.replace("_", "").isalnum():
            raise ValueError("Enter a valid username or mobile number")
        return value.lower()  # usernames are stored lower-cased


class EmailUpdate(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address")
        return value


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=8, max_length=200)


class VerifyConfirmRequest(BaseModel):
    code: str = Field(..., min_length=4, max_length=10)


class ForgotPasswordRequest(BaseModel):
    identifier: str = Field(..., min_length=3, max_length=255)  # username, mobile, or email


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=8, max_length=200)
    new_password: str = Field(..., min_length=6, max_length=100)
