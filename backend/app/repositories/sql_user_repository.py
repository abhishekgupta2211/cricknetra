"""SQL-backed user + profile repository."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import UserProfileRow, UserRow
from app.repositories.user_repository import (
    ProfileRecord,
    UserRecord,
    role_code,
    user_code,
)


def _pint(value: str) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_user(row: UserRow) -> UserRecord:
    return UserRecord(
        id=str(row.id), full_name=row.full_name, username=row.username, mobile_no=row.mobile_no,
        user_code=row.user_code, role_code=row.role_code, password=row.password, role=row.role,
        is_active=bool(row.is_active), is_verified=bool(row.is_verified), email=row.email,
        created_at=row.created_at or _now(), updated_at=row.updated_at or _now(),
    )


def _to_profile(row: UserProfileRow) -> ProfileRecord:
    return ProfileRecord(
        id=str(row.id), user_id=str(row.user_id), address=row.address, pincode=row.pincode,
        city=row.city, district=row.district, state=row.state, region=row.region,
        profile_picture=row.profile_picture, created_at=row.created_at or _now(),
        updated_at=row.updated_at or _now(),
    )


class SqlUserRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def add_user(self, full_name, username, mobile_no, password_hash, role, email=None) -> UserRecord:
        with self._sf() as s:
            total = s.query(func.count(UserRow.id)).scalar() or 0
            role_n = s.query(func.count(UserRow.id)).filter(UserRow.role == role).scalar() or 0
            row = UserRow(
                full_name=full_name, username=username, mobile_no=mobile_no, email=(email or None),
                user_code=user_code(total + 1), role_code=role_code(role, role_n + 1),
                password=password_hash, role=role, is_active=True, is_verified=False,
            )
            s.add(row)
            s.flush()
            s.refresh(row)  # pick up server-side timestamps
            rec = _to_user(row)
            s.commit()
            return rec

    def get_by_id(self, user_id) -> Optional[UserRecord]:
        uid = _pint(user_id)
        if uid is None:
            return None
        with self._sf() as s:
            row = s.get(UserRow, uid)
            return _to_user(row) if row else None

    def get_by_username(self, username) -> Optional[UserRecord]:
        with self._sf() as s:
            row = s.query(UserRow).filter(UserRow.username == username).first()
            return _to_user(row) if row else None

    def get_by_mobile(self, mobile_no) -> Optional[UserRecord]:
        with self._sf() as s:
            row = s.query(UserRow).filter(UserRow.mobile_no == mobile_no).first()
            return _to_user(row) if row else None

    def get_by_email(self, email) -> Optional[UserRecord]:
        e = (email or "").strip().lower()
        if not e:
            return None
        with self._sf() as s:
            row = s.query(UserRow).filter(func.lower(UserRow.email) == e).first()
            return _to_user(row) if row else None

    def get_by_identifier(self, identifier) -> Optional[UserRecord]:
        with self._sf() as s:
            row = (
                s.query(UserRow)
                .filter(or_(UserRow.username == identifier, UserRow.mobile_no == identifier))
                .first()
            )
            return _to_user(row) if row else None

    def list_users(self, role=None) -> list[UserRecord]:
        with self._sf() as s:
            q = s.query(UserRow).filter(UserRow.is_active.is_(True))
            if role:
                q = q.filter(UserRow.role == role)
            return [_to_user(r) for r in q.order_by(UserRow.full_name).all()]

    def set_role(self, user_id, new_role) -> Optional[UserRecord]:
        uid = _pint(user_id)
        if uid is None:
            return None
        with self._sf() as s:
            row = s.get(UserRow, uid)
            if row is None:
                return None
            role_n = s.query(func.count(UserRow.id)).filter(UserRow.role == new_role).scalar() or 0
            row.role = new_role
            row.role_code = role_code(new_role, role_n + 1)
            s.flush()
            s.refresh(row)
            rec = _to_user(row)
            s.commit()
            return rec

    def set_verified(self, user_id, value) -> Optional[UserRecord]:
        return self._patch(user_id, is_verified=bool(value))

    def set_password(self, user_id, password_hash) -> Optional[UserRecord]:
        return self._patch(user_id, password=password_hash)

    def set_email(self, user_id, email) -> Optional[UserRecord]:
        return self._patch(user_id, email=(email or None))

    def _patch(self, user_id, **fields) -> Optional[UserRecord]:
        uid = _pint(user_id)
        if uid is None:
            return None
        with self._sf() as s:
            row = s.get(UserRow, uid)
            if row is None:
                return None
            for key, value in fields.items():
                setattr(row, key, value)
            s.flush()
            s.refresh(row)
            rec = _to_user(row)
            s.commit()
            return rec

    def add_profile(self, user_id, address, pincode, city, district, state, region, profile_picture) -> ProfileRecord:
        uid = _pint(user_id)
        with self._sf() as s:
            row = UserProfileRow(
                user_id=uid, address=address, pincode=pincode, city=city, district=district,
                state=state, region=region, profile_picture=profile_picture,
            )
            s.add(row)
            s.flush()
            s.refresh(row)
            rec = _to_profile(row)
            s.commit()
            return rec

    def get_profile(self, user_id) -> Optional[ProfileRecord]:
        uid = _pint(user_id)
        if uid is None:
            return None
        with self._sf() as s:
            row = s.query(UserProfileRow).filter(UserProfileRow.user_id == uid).first()
            return _to_profile(row) if row else None

    def update_profile(self, user_id, **fields) -> Optional[ProfileRecord]:
        uid = _pint(user_id)
        if uid is None:
            return None
        with self._sf() as s:
            row = s.query(UserProfileRow).filter(UserProfileRow.user_id == uid).first()
            if row is None:
                return None
            for key, value in fields.items():
                if value is not None and hasattr(row, key):
                    setattr(row, key, value)
            s.flush()
            s.refresh(row)
            rec = _to_profile(row)
            s.commit()
            return rec
