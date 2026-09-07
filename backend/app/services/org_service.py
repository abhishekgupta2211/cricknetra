"""Areas, organizations, organizers, and the one place a role is assigned.

An **area** is a place ("Prayagraj"), an **organization** is a body that runs
cricket there, and an **organizer profile** ties a user account to both. Only an
admin writes any of it.

Two rules this service exists to hold:

* **Promotion, not creation.** Making somebody an organizer takes a `user_id`
  that already exists. There is one way to get an account (sign-up, with its
  password policy and verification), and this is not a second one — an unknown
  id is a 404, never a new row in ``users``.
* **Demotion is not deletion.** Standing down an organizer deactivates their
  profile and drops the account to ``general_user``, and deliberately leaves
  their tournaments owned by them. Deleting a competition because its organizer
  left would destroy scorecards; an admin reassigns or deletes them on purpose.

Nothing here reads a role, a user id or an ownership value from a request body.
The caller is always the account the route authenticated.
"""

from __future__ import annotations

from typing import Optional

from app.core.permissions import Roles
from app.repositories.audit_repository import AuditActions
from app.repositories.org_repository import (
    AreaRecord,
    OrganizationRecord,
    OrganizerRecord,
    OrgRepository,
)
from app.repositories.ownership_repository import OwnershipRepository
from app.repositories.user_repository import UserRecord, UserRepository
from app.schemas.org import (
    AreaCreate,
    AreaDTO,
    OrganizationCreate,
    OrganizationDTO,
    OrganizerCreate,
    OrganizerDTO,
    OrganizerUpdate,
)
from app.services.audit_service import AuditService


class OrgError(Exception):
    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class OrgService:
    def __init__(
        self,
        orgs: OrgRepository,
        users: UserRepository,
        owners: OwnershipRepository,
        audit: Optional[AuditService] = None,
    ) -> None:
        self.orgs = orgs
        self.users = users
        self.owners = owners
        self.audit = audit

    # ----------------------------------------------------------------- areas

    def list_areas(self) -> list[AreaDTO]:
        return [self._area_dto(a) for a in self.orgs.list_areas()]

    def create_area(self, req: AreaCreate) -> AreaDTO:
        name = (req.name or "").strip()
        if not name:
            raise OrgError("An area needs a name.")
        existing = next(
            (a for a in self.orgs.list_areas() if a.name.lower() == name.lower()), None
        )
        if existing is not None:
            # Two "Prayagraj" rows would split its organizers between them, so
            # the second attempt is refused rather than silently duplicated.
            raise OrgError(f"An area called '{existing.name}' already exists.", 409)
        return self._area_dto(self.orgs.add_area(name, (req.state or "").strip() or None))

    def delete_area(self, area_id: str) -> None:
        if self.orgs.get_area(str(area_id)) is None:
            raise OrgError("Area not found", 404)
        self.orgs.delete_area(str(area_id))

    # --------------------------------------------------------- organizations

    def list_organizations(self, area_id: Optional[str] = None) -> list[OrganizationDTO]:
        return [self._organization_dto(o) for o in self.orgs.list_organizations(area_id)]

    def create_organization(self, req: OrganizationCreate) -> OrganizationDTO:
        name = (req.name or "").strip()
        if not name:
            raise OrgError("An organization needs a name.")
        area_id = self._require_area(req.area_id)
        return self._organization_dto(self.orgs.add_organization(name, area_id))

    def delete_organization(self, org_id: str) -> None:
        if self.orgs.get_organization(str(org_id)) is None:
            raise OrgError("Organization not found", 404)
        self.orgs.delete_organization(str(org_id))

    # ------------------------------------------------------------ organizers

    def list_organizers(self, area_id: Optional[str] = None) -> list[OrganizerDTO]:
        return [self._organizer_dto(o) for o in self.orgs.list_organizers(area_id)]

    def create_organizer(self, admin: UserRecord, req: OrganizerCreate) -> OrganizerDTO:
        """Promote an existing account and record where it works."""
        user = self.users.get_by_id(str(req.user_id))
        if user is None:
            raise OrgError(
                "No such user. An organizer is promoted from an account that already exists.",
                404,
            )
        area_id = self._require_area(req.area_id)
        organization_id = self._require_organization(req.organization_id)

        # Appointing somebody rewrites their role, so it has to pass the same
        # lockout guard as the role endpoint — otherwise "make the last admin an
        # organizer" is a way around it.
        if user.role != Roles.ORGANIZER:
            self._guard_last_admin(user, Roles.ORGANIZER)

        profile = self.orgs.upsert_organizer(
            user_id=str(user.id),
            area_id=area_id,
            organization_id=organization_id,
            created_by=str(admin.id),
        )
        if user.role != Roles.ORGANIZER:
            user = self.users.set_role(str(user.id), Roles.ORGANIZER) or user
        self._audit(
            admin, AuditActions.ORGANIZER_CREATED, "user", user.id,
            f"{user.full_name or user.username} is now an organizer",
        )
        return self._organizer_dto(profile, user)

    def update_organizer(self, user_id: str, req: OrganizerUpdate) -> OrganizerDTO:
        """Edit an organizer's posting, or suspend them without demoting them.

        Suspending (``is_active=False``) leaves the role in place: ScopeService
        refuses a deactivated profile, so the account stops being able to act
        while its history stays readable. Demotion is :meth:`deactivate_organizer`.
        """
        profile = self.orgs.get_organizer(str(user_id))
        if profile is None:
            raise OrgError("Organizer not found", 404)
        was_active = profile.is_active
        area_id = self._require_area(req.area_id)
        organization_id = self._require_organization(req.organization_id)

        if area_id or organization_id:
            profile = self.orgs.upsert_organizer(
                user_id=str(user_id), area_id=area_id, organization_id=organization_id,
                created_by=None,
            )
        # upsert reactivates as a side effect, so a PATCH that only moves
        # somebody's area must not quietly un-suspend them.
        desired = was_active if req.is_active is None else bool(req.is_active)
        if profile.is_active != desired:
            profile = self.orgs.set_organizer_active(str(user_id), desired) or profile
        return self._organizer_dto(profile)

    def deactivate_organizer(self, admin: UserRecord, user_id: str) -> None:
        """Stand an organizer down: suspend the profile, drop the account to
        ``general_user``, and leave every tournament they own exactly where it
        is so an admin can reassign or delete it deliberately."""
        profile = self.orgs.get_organizer(str(user_id))
        if profile is None:
            raise OrgError("Organizer not found", 404)
        self.orgs.set_organizer_active(str(user_id), False)
        user = self.users.get_by_id(str(user_id))
        if user is not None and user.role == Roles.ORGANIZER:
            self.users.set_role(str(user_id), Roles.GENERAL_USER)
        kept = len(self.owners.list_by_owner(str(user_id), "tournament"))
        self._audit(
            admin, AuditActions.ORGANIZER_DEACTIVATED, "user", user_id,
            f"deactivated; {kept} tournament(s) left with their owner",
        )

    # --------------------------------------------------------- role assignment

    def assign_role(self, admin: UserRecord, user_id: str, role: str) -> dict:
        """Set an account's role outright — the only path a role changes by.

        Refuses to demote the last admin: an empty admin set locks everybody
        out of exactly the endpoints needed to fix it.
        """
        new_role = (role or "").strip().lower()
        if new_role not in Roles.ASSIGNABLE:
            allowed = ", ".join(Roles.ASSIGNABLE)
            raise OrgError(f"'{role}' is not a role. Choose one of: {allowed}.")
        user = self.users.get_by_id(str(user_id))
        if user is None:
            raise OrgError("User not found", 404)
        self._guard_last_admin(user, new_role)
        previous = user.role
        updated = self.users.set_role(str(user.id), new_role)
        if updated is None:
            raise OrgError("User not found", 404)
        self._audit(
            admin, AuditActions.ROLE_ASSIGNED, "user", updated.id,
            f"{previous} -> {new_role}",
        )
        return {"user_id": updated.id, "role": updated.role, "role_code": updated.role_code}

    # ------------------------------------------------------------- internals

    def _admin_count(self) -> int:
        return sum(1 for u in self.users.list_users(role=Roles.ADMIN) if u.is_active)

    def _guard_last_admin(self, user: UserRecord, new_role: str) -> None:
        """Refuse any change that would empty the admin set.

        Every path that rewrites a role goes through here, not just the role
        endpoint: with no admin left, the endpoints needed to appoint one are
        themselves admin-only, and the deployment is unrecoverable from inside.
        """
        if user.role != Roles.ADMIN or new_role == Roles.ADMIN:
            return
        if self._admin_count() <= 1:
            raise OrgError(
                "This is the last admin — promote somebody else before demoting them.", 409
            )

    def _require_area(self, area_id: Optional[str]) -> Optional[str]:
        """Resolve an optional area reference, refusing one that doesn't exist —
        an organizer filed under a phantom area never shows up in any list."""
        if not area_id:
            return None
        if self.orgs.get_area(str(area_id)) is None:
            raise OrgError("Area not found", 404)
        return str(area_id)

    def _require_organization(self, org_id: Optional[str]) -> Optional[str]:
        if not org_id:
            return None
        if self.orgs.get_organization(str(org_id)) is None:
            raise OrgError("Organization not found", 404)
        return str(org_id)

    def _audit(
        self, admin: UserRecord, action: str, resource_type: str, resource_id: str, detail: str
    ) -> None:
        if self.audit is None:
            return
        self.audit.record(
            actor_id=str(admin.id), action=action, resource_type=resource_type,
            resource_id=str(resource_id), detail=detail,
        )

    def _tournament_count(self, user_id: str) -> int:
        return len(self.owners.list_by_owner(str(user_id), "tournament"))

    def _area_dto(self, area: AreaRecord) -> AreaDTO:
        # Tournaments have no area of their own — an area's competitions are the
        # ones its organizers run, which is the number an admin is looking for.
        organizers = [o for o in self.orgs.list_organizers(area.id) if o.is_active]
        return AreaDTO(
            id=area.id,
            name=area.name,
            state=area.state,
            organizers=len(organizers),
            tournaments=sum(self._tournament_count(o.user_id) for o in organizers),
        )

    def _organization_dto(self, org: OrganizationRecord) -> OrganizationDTO:
        area = self.orgs.get_area(org.area_id) if org.area_id else None
        return OrganizationDTO(
            id=org.id, name=org.name, area_id=org.area_id,
            area_name=area.name if area else None,
        )

    def _organizer_dto(
        self, profile: OrganizerRecord, user: Optional[UserRecord] = None
    ) -> OrganizerDTO:
        user = user or self.users.get_by_id(profile.user_id)
        area = self.orgs.get_area(profile.area_id) if profile.area_id else None
        org = (
            self.orgs.get_organization(profile.organization_id)
            if profile.organization_id
            else None
        )
        return OrganizerDTO(
            user_id=profile.user_id,
            full_name=getattr(user, "full_name", "") or "",
            username=getattr(user, "username", "") or "",
            mobile_no=getattr(user, "mobile_no", "") or "",
            role=getattr(user, "role", "") or "",
            # The *profile's* standing, which is what this screen manages — a
            # suspended organizer may still have a perfectly active account.
            is_active=profile.is_active,
            area_id=profile.area_id,
            area_name=area.name if area else None,
            organization_id=profile.organization_id,
            organization_name=org.name if org else None,
            tournaments=self._tournament_count(profile.user_id),
            created_at=profile.created_at.isoformat() if profile.created_at else None,
        )
