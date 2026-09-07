"""Community / social DTOs."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class FollowState(BaseModel):
    is_following: bool
    followers: int
    following: int


class ActivityDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    actor_id: str
    actor_name: str
    kind: str
    text: str
    link: str
    when: str


class NotificationDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    kind: str
    text: str
    link: str
    is_read: bool
    when: str
    category: str = ""
    title: str = ""
    count: int = 1        # events folded into this one (coalescing)


class EntityFollowState(BaseModel):
    is_following: bool
    followers: int


class NotificationPrefs(BaseModel):
    """Category toggles + delivery channels. Extra/unknown keys are ignored on write."""
    model_config = ConfigDict(extra="ignore")
    match: bool = True
    tournament: bool = True
    team: bool = True
    player: bool = True
    social: bool = True
    system: bool = True
    achievement: bool = True
    marketing: bool = False
    email_enabled: bool = False
    push_enabled: bool = True
    sound: bool = True
    quiet_start: "int | None" = Field(default=None, ge=0, le=23)   # local hour (DND from)
    quiet_end: "int | None" = Field(default=None, ge=0, le=23)     # local hour (DND to)
    tz_offset: int = Field(default=0, ge=-720, le=840)             # minutes UTC→local


class VapidKey(BaseModel):
    key: str
    available: bool


class PushKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscribeRequest(BaseModel):
    """The browser's PushSubscription.toJSON() shape (endpoint + keys), plus platform."""
    model_config = ConfigDict(extra="ignore")
    endpoint: str
    keys: PushKeys
    platform: str = "web"


class PushUnsubscribeRequest(BaseModel):
    endpoint: str


class AnnouncementCreate(BaseModel):
    """An admin broadcast. `category` is system (important) or marketing (opt-out)."""
    model_config = ConfigDict(extra="ignore")
    title: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=255)
    category: str = "system"
    link: str = ""


class AnnouncementResult(BaseModel):
    campaign_id: str
    recipients: int      # delivered to (after opt-outs)
    audience: int        # total active users considered


class CampaignAnalyticsDTO(BaseModel):
    id: str
    title: str
    text: str
    category: str
    link: str
    recipients: int
    when: str
    delivered: int
    opened: int
    clicked: int
    open_rate: float
    ctr: float


class PushRotateRequest(BaseModel):
    """Sent by the SW's pushsubscriptionchange handler (no auth — the old endpoint
    is the identity). Rotates an existing subscription to its new endpoint/keys."""
    model_config = ConfigDict(extra="ignore")
    old_endpoint: "str | None" = None
    endpoint: str
    keys: PushKeys
    platform: str = "web"
