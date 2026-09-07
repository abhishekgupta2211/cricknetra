"""Organizers, and the areas and organizations they run competitions for.

An **area** is a place ("Prayagraj"); an **organization** is a body that runs
cricket there ("XYZ Sports"); an **organizer** is a user account tied to both.
Admin owns all three. An organizer reads them but never writes them.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------- areas / orgs

class AreaCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    state: Optional[str] = Field(default=None, max_length=80)


class AreaDTO(BaseModel):
    id: str
    name: str
    state: Optional[str] = None
    organizers: int = 0       # how many organizers work here
    tournaments: int = 0


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=140)
    area_id: Optional[str] = Field(default=None, max_length=40)


class OrganizationDTO(BaseModel):
    id: str
    name: str
    area_id: Optional[str] = None
    area_name: Optional[str] = None


# ------------------------------------------------------------------ organizer

class OrganizerCreate(BaseModel):
    """Promote an existing account to organizer, and say where they work.

    Deliberately takes an existing `user_id` rather than creating an account:
    the person signs up themselves like everybody else, and the admin then
    grants the role. That keeps one account-creation path, with one password
    policy and one verification flow.
    """

    user_id: str = Field(..., max_length=40)
    area_id: Optional[str] = Field(default=None, max_length=40)
    organization_id: Optional[str] = Field(default=None, max_length=40)


class OrganizerUpdate(BaseModel):
    area_id: Optional[str] = Field(default=None, max_length=40)
    organization_id: Optional[str] = Field(default=None, max_length=40)
    is_active: Optional[bool] = None


class OrganizerDTO(BaseModel):
    user_id: str
    full_name: str = ""
    username: str = ""
    mobile_no: str = ""
    role: str = ""
    is_active: bool = True

    area_id: Optional[str] = None
    area_name: Optional[str] = None
    organization_id: Optional[str] = None
    organization_name: Optional[str] = None

    tournaments: int = 0      # how many competitions they run
    created_at: Optional[str] = None


# ------------------------------------------------------------ role assignment

class RoleAssign(BaseModel):
    """Admin sets an account's role outright.

    This is the only way a role changes. Sign-up cannot grant one, and no
    endpoint reads a role from the request body when deciding what a caller
    may do — the role always comes from the authenticated account.
    """

    role: str = Field(..., min_length=3, max_length=50)


# -------------------------------------------------------------------- staff

class StaffAdd(BaseModel):
    """Put an umpire or commentator on a tournament's staff."""

    user_id: str = Field(..., max_length=40)


class StaffDTO(BaseModel):
    user_id: str
    full_name: str = ""
    username: str = ""
    mobile_no: str = ""
    staff_role: str = ""          # umpire | commentator
    is_active: bool = True
    tournament_id: str = ""
    added_by: Optional[str] = None


# --------------------------------------------------------------------- audit

class AuditDTO(BaseModel):
    id: str
    actor_id: Optional[str] = None
    actor_name: str = ""
    action: str
    resource_type: str = ""
    resource_id: str = ""
    detail: str = ""
    when: Optional[str] = None
