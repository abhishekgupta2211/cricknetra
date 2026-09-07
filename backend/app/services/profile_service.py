"""ProfileService — the user's location/profile, on top of the user repository.

Adapted from the user-supplied ``profile_service.py``: repository-backed, raises
a domain ``ProfileError``, and uses attribute access consistently (the original
``complete_profile`` mixed ``payload["address"]`` with ``payload.address``).
"""

from __future__ import annotations

from app.repositories.user_repository import ProfileRecord, UserRecord, UserRepository
from app.schemas.profile import ProfileCompleteRequest


class ProfileError(Exception):
    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


class ProfileService:
    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    def complete(self, user: UserRecord, payload: ProfileCompleteRequest) -> ProfileRecord:
        if self.repo.get_profile(user.id) is not None:
            raise ProfileError("Profile already completed", 409)
        return self.repo.add_profile(
            user_id=user.id,
            address=payload.address.strip(),
            pincode=payload.pincode.strip(),
            city=payload.city.strip(),
            district=payload.district.strip(),
            state=payload.state.strip(),
            region=payload.region.strip(),
            profile_picture=_clean(payload.profile_picture),
        )

    def get(self, user: UserRecord) -> ProfileRecord:
        profile = self.repo.get_profile(user.id)
        if profile is None:
            raise ProfileError("Profile not completed yet", 404)
        return profile

    def update(self, user: UserRecord, payload: ProfileCompleteRequest) -> ProfileRecord:
        if self.repo.get_profile(user.id) is None:
            raise ProfileError("Profile not completed yet", 404)
        return self.repo.update_profile(
            user.id,
            address=payload.address.strip(),
            pincode=payload.pincode.strip(),
            city=payload.city.strip(),
            district=payload.district.strip(),
            state=payload.state.strip(),
            region=payload.region.strip(),
            profile_picture=_clean(payload.profile_picture),
        )
