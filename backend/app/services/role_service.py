"""Elevated-role approval — admin grants/declines pending role requests.

Sign-up records a pending request (the user is a ``general_user`` until then);
approving promotes the user to the requested role (recomputing their role_code),
and either decision notifies the user.
"""

from __future__ import annotations

from typing import Optional

from app.repositories.role_request_repository import RoleRequestRepository
from app.repositories.user_repository import UserRepository


class RoleError(Exception):
    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class RoleService:
    def __init__(self, users: UserRepository, requests: RoleRequestRepository, social=None) -> None:
        self.users = users
        self.requests = requests
        self.social = social  # optional social repo (add_notification) for user alerts

    def status_for(self, user_id: str) -> tuple[bool, Optional[str]]:
        """(is_pending, requested_role) for the given user."""
        req = self.requests.pending_for(user_id)
        return (req is not None, req.requested_role if req else None)

    def list_pending(self) -> list[dict]:
        out: list[dict] = []
        for r in self.requests.list_pending():
            u = self.users.get_by_id(r.user_id)
            if u is None:
                continue
            out.append({
                "user_id": r.user_id, "full_name": u.full_name, "username": u.username,
                "requested_role": r.requested_role, "when": r.when,
            })
        return out

    def approve(self, user_id: str) -> dict:
        req = self.requests.pending_for(user_id)
        if req is None:
            raise RoleError("No pending role request for this user", 404)
        user = self.users.set_role(user_id, req.requested_role)
        if user is None:
            raise RoleError("User not found", 404)
        self.requests.set_status(user_id, "approved")
        self._notify(user_id, f"Your {self._label(req.requested_role)} role was approved 🎉")
        return {"user_id": user_id, "role": user.role, "role_code": user.role_code}

    def reject(self, user_id: str) -> None:
        req = self.requests.pending_for(user_id)
        if req is None:
            raise RoleError("No pending role request for this user", 404)
        self.requests.set_status(user_id, "rejected")
        self._notify(user_id, f"Your {self._label(req.requested_role)} role request was declined")

    @staticmethod
    def _label(role: str) -> str:
        return role.replace("_", " ")

    def _notify(self, user_id: str, text: str) -> None:
        if self.social is not None:
            self.social.add_notification(user_id, "role", text, "#/account")
