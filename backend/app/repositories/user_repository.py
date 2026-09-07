"""User + profile storage interface and in-memory implementation.

Keeps auth on the same repository pattern as the rest of CricNetra, so the test
suite runs without a database. `user_code` / `role_code` are generated here (the
behaviour of the user-supplied ``generate_user_code`` / ``generate_role_code``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import count
from typing import Optional, Protocol

# Short prefixes per role for the human-facing role_code (e.g. PLY001, UMP001).
ROLE_PREFIX = {
    "player": "PLY",
    "umpire": "UMP",
    "commentator": "COM",
    "organizer": "ORG",
    "team_owner": "TMO",
    "admin": "ADM",
    "general_user": "GEN",
}


def user_code(n: int) -> str:
    return f"CN{n:06d}"


def role_code(role: str, n: int) -> str:
    return f"{ROLE_PREFIX.get(role, 'GEN')}{n:03d}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class UserRecord:
    id: str
    full_name: str
    username: str
    mobile_no: str
    user_code: str
    role_code: str
    password: str  # argon2 hash
    role: str
    is_active: bool = True
    is_verified: bool = False
    email: Optional[str] = None  # for email OTP / password-reset delivery
    created_at: datetime = None  # type: ignore[assignment]
    updated_at: datetime = None  # type: ignore[assignment]


@dataclass
class ProfileRecord:
    id: str
    user_id: str
    address: str
    pincode: str
    city: str
    district: str
    state: str
    region: str
    profile_picture: Optional[str] = None
    created_at: datetime = None  # type: ignore[assignment]
    updated_at: datetime = None  # type: ignore[assignment]


class UserRepository(Protocol):
    def add_user(self, full_name: str, username: str, mobile_no: str, password_hash: str, role: str, email: Optional[str] = None) -> UserRecord: ...
    def get_by_id(self, user_id: str) -> Optional[UserRecord]: ...
    def get_by_username(self, username: str) -> Optional[UserRecord]: ...
    def get_by_mobile(self, mobile_no: str) -> Optional[UserRecord]: ...
    def get_by_email(self, email: str) -> Optional[UserRecord]: ...
    def get_by_identifier(self, identifier: str) -> Optional[UserRecord]: ...
    def list_users(self, role: Optional[str] = None) -> list[UserRecord]: ...
    def set_role(self, user_id: str, new_role: str) -> Optional[UserRecord]: ...
    def set_verified(self, user_id: str, value: bool) -> Optional[UserRecord]: ...
    def set_password(self, user_id: str, password_hash: str) -> Optional[UserRecord]: ...
    def set_email(self, user_id: str, email: Optional[str]) -> Optional[UserRecord]: ...
    # profiles
    def add_profile(self, user_id: str, address: str, pincode: str, city: str, district: str, state: str, region: str, profile_picture: Optional[str]) -> ProfileRecord: ...
    def get_profile(self, user_id: str) -> Optional[ProfileRecord]: ...
    def update_profile(self, user_id: str, **fields) -> Optional[ProfileRecord]: ...


class InMemoryUserRepository:
    def __init__(self) -> None:
        self._users: dict[str, UserRecord] = {}
        self._profiles: dict[str, ProfileRecord] = {}  # keyed by user_id
        self._uids = count(1)
        self._pids = count(1)

    def add_user(self, full_name, username, mobile_no, password_hash, role, email=None) -> UserRecord:
        uid = str(next(self._uids))
        total = len(self._users) + 1
        role_n = sum(1 for u in self._users.values() if u.role == role) + 1
        now = _now()
        rec = UserRecord(
            id=uid, full_name=full_name, username=username, mobile_no=mobile_no,
            user_code=user_code(total), role_code=role_code(role, role_n),
            password=password_hash, role=role, is_active=True, is_verified=False,
            email=(email or None), created_at=now, updated_at=now,
        )
        self._users[uid] = rec
        return rec

    def get_by_id(self, user_id) -> Optional[UserRecord]:
        return self._users.get(str(user_id))

    def get_by_username(self, username) -> Optional[UserRecord]:
        return next((u for u in self._users.values() if u.username == username), None)

    def get_by_mobile(self, mobile_no) -> Optional[UserRecord]:
        return next((u for u in self._users.values() if u.mobile_no == mobile_no), None)

    def get_by_email(self, email) -> Optional[UserRecord]:
        e = (email or "").strip().lower()
        if not e:
            return None
        return next((u for u in self._users.values() if (getattr(u, "email", None) or "").lower() == e), None)

    def get_by_identifier(self, identifier) -> Optional[UserRecord]:
        return self.get_by_username(identifier) or self.get_by_mobile(identifier)

    def list_users(self, role=None) -> list[UserRecord]:
        users = [u for u in self._users.values() if u.is_active]
        if role:
            users = [u for u in users if u.role == role]
        return sorted(users, key=lambda u: u.full_name.lower())

    def set_role(self, user_id, new_role) -> Optional[UserRecord]:
        rec = self._users.get(str(user_id))
        if rec is None:
            return None
        role_n = sum(1 for u in self._users.values() if u.role == new_role) + 1
        rec.role = new_role
        rec.role_code = role_code(new_role, role_n)
        rec.updated_at = _now()
        return rec

    def set_verified(self, user_id, value) -> Optional[UserRecord]:
        rec = self._users.get(str(user_id))
        if rec is not None:
            rec.is_verified = bool(value)
            rec.updated_at = _now()
        return rec

    def set_password(self, user_id, password_hash) -> Optional[UserRecord]:
        rec = self._users.get(str(user_id))
        if rec is not None:
            rec.password = password_hash
            rec.updated_at = _now()
        return rec

    def set_email(self, user_id, email) -> Optional[UserRecord]:
        rec = self._users.get(str(user_id))
        if rec is not None:
            rec.email = (email or None)
            rec.updated_at = _now()
        return rec

    def add_profile(self, user_id, address, pincode, city, district, state, region, profile_picture) -> ProfileRecord:
        pid = str(next(self._pids))
        now = _now()
        rec = ProfileRecord(
            id=pid, user_id=str(user_id), address=address, pincode=pincode, city=city,
            district=district, state=state, region=region, profile_picture=profile_picture,
            created_at=now, updated_at=now,
        )
        self._profiles[str(user_id)] = rec
        return rec

    def get_profile(self, user_id) -> Optional[ProfileRecord]:
        return self._profiles.get(str(user_id))

    def update_profile(self, user_id, **fields) -> Optional[ProfileRecord]:
        rec = self._profiles.get(str(user_id))
        if rec is None:
            return None
        for key, value in fields.items():
            if value is not None and hasattr(rec, key):
                setattr(rec, key, value)
        rec.updated_at = _now()
        return rec
