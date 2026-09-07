"""ORM models — an event-sourced schema.

We persist the *match setup* (rules, teams, squads) plus the **append-only ball
log**. The full scorecard/stats are never stored; they're rebuilt by replaying
the events through the engine. JSONB on Postgres (generic JSON elsewhere, so the
same models run on SQLite in tests).
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, LargeBinary, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# JSONB on Postgres, plain JSON on SQLite/others — lets tests run without PG.
JSONType = JSON().with_variant(JSONB, "postgresql")


class MatchRow(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_a: Mapped[str] = mapped_column(String(120))
    team_b: Mapped[str] = mapped_column(String(120))
    bat_first: Mapped[str] = mapped_column(String(120))
    format_id: Mapped[str] = mapped_column(String(40))
    rules: Mapped[dict] = mapped_column(JSONType)
    squad_a: Mapped[list] = mapped_column(JSONType)
    squad_b: Mapped[list] = mapped_column(JSONType)
    second_innings_started: Mapped[bool] = mapped_column(default=False)
    pending_bowler: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    result: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="in_progress")
    # bring-your-own live-stream link (YouTube/Facebook); metadata, not a ball event.
    stream_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # bring-your-own highlight clips: list of {id, url, label}. Embeds computed on read.
    clips: Mapped[Optional[list]] = mapped_column(JSONType, nullable=True)
    # display-only match metadata: {venue, tournament, match_no, toss_winner, toss_decision}.
    # Not scoring rules — kept out of the `rules` blob on purpose.
    meta: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class BallEventRow(Base):
    __tablename__ = "ball_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), index=True
    )
    innings_number: Mapped[int] = mapped_column(Integer)  # 1 or 2
    seq: Mapped[int] = mapped_column(Integer)  # order within the innings
    payload: Mapped[dict] = mapped_column(JSONType)  # BallEvent.model_dump(mode="json")

    __table_args__ = (
        Index("ix_ball_events_match_innings_seq", "match_id", "innings_number", "seq"),
    )


class RuleTemplateRow(Base):
    """A saved, named rulebook (the output of the custom-rule builder)."""

    __tablename__ = "rule_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120))
    rules: Mapped[dict] = mapped_column(JSONType)  # MatchRules.model_dump(mode="json")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PlayerRow(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    batting_style: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    bowling_style: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    # the user account that has claimed this roster player (the unverified-stub →
    # claim model). Null = unclaimed. Stored as a string id (no hard FK, mirrors
    # resource_owners / member_activity).
    user_id: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class TeamRow(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120))
    location: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class TeamMemberRow(Base):
    __tablename__ = "team_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"), index=True)
    is_captain: Mapped[bool] = mapped_column(default=False)
    sort_order: Mapped[int] = mapped_column(default=0)

    __table_args__ = (UniqueConstraint("team_id", "player_id", name="uq_team_player"),)


class MatchPlayerRow(Base):
    """Links a real player to the name they batted/bowled under in a match, so
    per-player career stats can be aggregated from the (name-keyed) ball log."""

    __tablename__ = "match_players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))  # the scoring name within the match
    side: Mapped[str] = mapped_column(String(1))  # 'a' or 'b'
    team_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)


class TournamentRow(Base):
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(160))
    format: Mapped[str] = mapped_column(String(20))  # 'round_robin' | 'knockout' | 'groups'
    rules: Mapped[dict] = mapped_column(JSONType)  # MatchRules snapshot for its matches
    team_ids: Mapped[list] = mapped_column(JSONType)  # ordered participating team ids
    # tournament-level settings kept out of the MatchRules snapshot: points config
    # (win/tie/nr), and for the 'groups' format num_groups / advance_per_group /
    # the pool membership map {"A": [team_id, ...], ...}.
    config: Mapped[dict] = mapped_column(JSONType, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class FixtureRow(Base):
    __tablename__ = "fixtures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("tournaments.id", ondelete="CASCADE"), index=True
    )
    round: Mapped[int] = mapped_column(Integer, default=1)
    position: Mapped[int] = mapped_column(Integer, default=0)
    team_a_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    team_b_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    match_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="scheduled")  # scheduled|live|completed
    winner_team_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # pool label ("A"/"B"/…) for a group-stage fixture; NULL = playoff/bracket fixture.
    group: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)


# --------------------------------------------------------------------------- #
# Auth — users & profiles (phone + username + password, role-based)
# --------------------------------------------------------------------------- #
class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(100))
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    mobile_no: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # OTP/reset delivery
    user_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    role_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    password: Mapped[str] = mapped_column(String(255))  # argon2 hash
    role: Mapped[str] = mapped_column(String(50), default="general_user")
    is_active: Mapped[bool] = mapped_column(default=True)
    is_verified: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UserProfileRow(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    address: Mapped[str] = mapped_column(String(255))
    pincode: Mapped[str] = mapped_column(String(10))
    city: Mapped[str] = mapped_column(String(100))
    district: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(100))
    region: Mapped[str] = mapped_column(String(100))
    profile_picture: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ResourceOwnerRow(Base):
    """Who created a match / team / tournament (for edit/delete permissions)."""

    __tablename__ = "resource_owners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resource_type: Mapped[str] = mapped_column(String(20), index=True)  # match|team|tournament
    resource_id: Mapped[str] = mapped_column(String(40), index=True)
    owner_id: Mapped[str] = mapped_column(String(40), index=True)

    __table_args__ = (
        UniqueConstraint("resource_type", "resource_id", name="uq_resource_owner"),
    )


class TournamentSquadRow(Base):
    """A player registered to a team **for a specific tournament**. The unique
    (tournament_id, player_id) constraint enforces the rule that a player can be
    in only one team's squad per tournament (but is free across tournaments)."""

    __tablename__ = "tournament_squads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(
        ForeignKey("tournaments.id", ondelete="CASCADE"), index=True
    )
    team_id: Mapped[int] = mapped_column(Integer, index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"), index=True)

    __table_args__ = (
        UniqueConstraint("tournament_id", "player_id", name="uq_tournament_player"),
    )


class MemberActivityRow(Base):
    """A member's records — e.g. matches they umpired / commentated. (Owned-resource
    counts come from resource_owners; this captures activity that isn't ownership.)"""

    __tablename__ = "member_activity"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(30), index=True)  # match_umpired|match_commentated
    resource_id: Mapped[str] = mapped_column(String(40))

    __table_args__ = (
        UniqueConstraint("user_id", "kind", "resource_id", name="uq_member_activity"),
    )


# --------------------------------------------------------------------------- #
# Community / social — follow graph, activity feed, notifications
# --------------------------------------------------------------------------- #
class FollowRow(Base):
    """follower_id follows followee_id (both are user ids)."""

    __tablename__ = "follows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    follower_id: Mapped[str] = mapped_column(String(40), index=True)
    followee_id: Mapped[str] = mapped_column(String(40), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("follower_id", "followee_id", name="uq_follow"),)


class EntityFollowRow(Base):
    """A user follows a non-user entity (team|player|tournament|match|club|academy) —
    the subscription graph that decides who receives an entity's notifications."""

    __tablename__ = "entity_follows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    follower_id: Mapped[str] = mapped_column(String(40), index=True)
    entity_type: Mapped[str] = mapped_column(String(20))
    entity_id: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("follower_id", "entity_type", "entity_id", name="uq_entity_follow"),
        Index("ix_entity_follow_target", "entity_type", "entity_id"),
    )


class NotificationPrefRow(Base):
    """Per-user notification preferences (one row per user) — category toggles, the
    delivery channels, quiet hours (DND window) and the notification sound."""

    __tablename__ = "notification_prefs"

    user_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    match: Mapped[bool] = mapped_column(default=True)
    tournament: Mapped[bool] = mapped_column(default=True)
    team: Mapped[bool] = mapped_column(default=True)
    player: Mapped[bool] = mapped_column(default=True)
    social: Mapped[bool] = mapped_column(default=True)
    system: Mapped[bool] = mapped_column(default=True)
    achievement: Mapped[bool] = mapped_column(default=True)
    marketing: Mapped[bool] = mapped_column(default=False)
    email_enabled: Mapped[bool] = mapped_column(default=False)
    push_enabled: Mapped[bool] = mapped_column(default=True)
    sound: Mapped[bool] = mapped_column(default=True)                   # play a chime in-app
    quiet_start: Mapped[Optional[int]] = mapped_column(nullable=True)   # local hour 0-23 (DND from)
    quiet_end: Mapped[Optional[int]] = mapped_column(nullable=True)     # local hour 0-23 (DND to)
    tz_offset: Mapped[int] = mapped_column(default=0)                   # minutes to add to UTC → local
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PushSubscriptionRow(Base):
    """A browser/device Web-Push subscription for a user (one row per endpoint)."""

    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(40), index=True)
    endpoint: Mapped[str] = mapped_column(String(500))
    p256dh: Mapped[str] = mapped_column(String(120))
    auth: Mapped[str] = mapped_column(String(60))
    platform: Mapped[str] = mapped_column(String(20), default="web")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (UniqueConstraint("endpoint", name="uq_push_endpoint"),)


class ActivityRow(Base):
    """A feed entry — 'actor did something' (match scored, tournament created…)."""

    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[str] = mapped_column(String(40), index=True)
    actor_name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(30))  # match|tournament|team
    text: Mapped[str] = mapped_column(String(255))
    link: Mapped[str] = mapped_column(String(160), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class NotificationRow(Base):
    """A notification delivered to a recipient user."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(40), index=True)  # recipient
    kind: Mapped[str] = mapped_column(String(30))  # follow|activity|message|role|official|match|...
    text: Mapped[str] = mapped_column(String(255))
    link: Mapped[str] = mapped_column(String(160), default="")
    is_read: Mapped[bool] = mapped_column(default=False, index=True)
    # richer metadata (all optional — old rows carry NULLs, defaults derived on read)
    category: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)   # match|tournament|team|player|social|system|achievement|admin
    title: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    data: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)
    # coalescing key: a fresh burst of the same group_key folds into one unread row (P3)
    group_key: Mapped[Optional[str]] = mapped_column(String(60), nullable=True, index=True)
    # engagement funnel (P5): which admin campaign this came from + open/click timestamps.
    # delivered == created_at; opened_at set when read; clicked_at when the link is opened.
    campaign_id: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, index=True)
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    clicked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class AnnouncementRow(Base):
    """An admin broadcast campaign — the source of the notifications tagged with its id,
    so we can measure delivered / opened / clicked for it."""

    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(120))
    text: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(20), default="system")
    link: Mapped[str] = mapped_column(String(160), default="")
    created_by: Mapped[str] = mapped_column(String(40))          # the admin's user id
    audience: Mapped[str] = mapped_column(String(20), default="all")
    recipients: Mapped[int] = mapped_column(Integer, default=0)  # how many it was delivered to
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AwardRow(Base):
    """A match award (Man of the Match / best batter / best bowler), persisted so a
    player's profile can show their honours and so each winner is notified once."""

    __tablename__ = "awards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(String(40), index=True)
    award_type: Mapped[str] = mapped_column(String(20))                 # mom | best_bat | best_bowl
    player_key: Mapped[str] = mapped_column(String(60), index=True)     # the "player" follow entity_id
    player_name: Mapped[str] = mapped_column(String(100))
    detail: Mapped[str] = mapped_column(String(80), default="")         # e.g. "82 (45)" / "5/24"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("match_id", "award_type", name="uq_award_match_type"),)


class PhotoRow(Base):
    """A profile / player picture, stored as bytes. One row per (kind, owner).

    A standalone table so it's created by ``create_all`` without a migration, and
    so large image blobs never bloat the player/user rows that are read often.
    """

    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(16), index=True)   # "player" | "user"
    owner_id: Mapped[str] = mapped_column(String(40), index=True)
    content_type: Mapped[str] = mapped_column(String(60))
    data: Mapped[bytes] = mapped_column(LargeBinary)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (UniqueConstraint("kind", "owner_id", name="uq_photo_owner"),)


class AuthTokenRow(Base):
    """Short-lived single-use tokens: mobile verification codes + password resets.

    Only the SHA-256 hash of the code/token is stored, never the raw value.
    """

    __tablename__ = "auth_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)  # verify | reset
    token_hash: Mapped[str] = mapped_column(String(255), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RoleRequestRow(Base):
    """A request to be granted an elevated role, awaiting admin approval."""

    __tablename__ = "role_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(40), index=True)
    requested_role: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending|approved|rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class MatchOfficialRow(Base):
    """An umpire's request to officiate a match, approved by the match's owner."""

    __tablename__ = "match_officials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(String(40), index=True)
    umpire_id: Mapped[str] = mapped_column(String(40), index=True)
    umpire_name: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending|approved
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("match_id", "umpire_id", name="uq_match_official"),)


class CommentaryRow(Base):
    """A live-commentary line posted on a match by a commentator."""

    __tablename__ = "commentary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(String(40), index=True)
    author_id: Mapped[str] = mapped_column(String(40), index=True)
    author_name: Mapped[str] = mapped_column(String(100))
    text: Mapped[str] = mapped_column(String(280))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class MessageRow(Base):
    """A direct 1:1 message between two users. `pair_key` is the canonical
    "minId:maxId" of the two participants so a conversation is one indexed lookup."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pair_key: Mapped[str] = mapped_column(String(81), index=True)  # "min:max" of the two ids
    sender_id: Mapped[str] = mapped_column(String(40), index=True)
    recipient_id: Mapped[str] = mapped_column(String(40), index=True)
    text: Mapped[str] = mapped_column(String(2000))
    is_read: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class LookingForRow(Base):
    """A "Looking For" board post — a player seeking a team, a team seeking
    players, or either seeking a match/opponent."""

    __tablename__ = "looking_for"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    author_id: Mapped[str] = mapped_column(String(40), index=True)
    author_name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(20), index=True)  # player | team | match
    text: Mapped[str] = mapped_column(String(500))
    location: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    role: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)  # e.g. "all-rounder"
    status: Mapped[str] = mapped_column(String(12), default="open", index=True)  # open | closed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class VenueRow(Base):
    """A ground or coaching academy — a searchable directory entry. Standalone
    table (create_all makes it) with a guarded migration for the Alembic chain."""

    __tablename__ = "venues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    kind: Mapped[str] = mapped_column(String(16), index=True)  # ground | academy
    city: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class FieldingEventRow(Base):
    """A non-delivery fielding note on a match — a dropped catch, runs saved, or a
    misfield. Deliberately kept OUT of the ball log (these aren't deliveries); a
    standalone table so create_all makes it, with a guarded migration for the chain."""

    __tablename__ = "fielding_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(String(40), index=True)
    innings: Mapped[int] = mapped_column(Integer, default=1)
    fielder: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(16), index=True)  # drop | save | misfield
    runs: Mapped[int] = mapped_column(Integer, default=0)  # saved (save) / conceded (misfield)
    bowler: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)  # denied the wicket (drop)
    batter: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)  # let off (drop)
    note: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    over_ball: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


# --------------------------------------------------------------------------- #
# Organizers, the places they work, their staff, and the audit trail
#
# These four registries were process-local until now: their repositories had no
# SQL implementation, so on a Postgres deployment they lived only in the worker
# that wrote them and vanished on restart. The audit trail is the sharpest case
# — a record of who granted a role or destroyed a competition is worth nothing
# if it is lost by the next deploy — but an organizer profile is load-bearing
# too, because ScopeService refuses a deactivated organizer and cannot see a
# profile that another worker holds in memory.
#
# User, tournament and team references are stored as strings with no foreign
# key, exactly as resource_owners / member_activity / match_officials already
# do: these are side registries that must outlive what they point at (the trail
# still names an account that has since been deleted).
# --------------------------------------------------------------------------- #
class AreaRow(Base):
    """A place cricket is run in ("Prayagraj").

    No unique constraint on the name: OrgService already refuses a duplicate
    case-insensitively, and a plain UNIQUE here would be case-sensitive on
    Postgres — it would let "prayagraj" in beside "Prayagraj" while claiming to
    prevent exactly that, which is worse than no constraint at all.
    """

    __tablename__ = "areas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    state: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OrganizationRow(Base):
    """A body that runs cricket in an area ("XYZ Sports")."""

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(140), index=True)
    area_id: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OrganizerProfileRow(Base):
    """One account's standing as an organizer — where they work and whether the
    posting is still active.

    ``user_id`` is unique because the in-memory repository keys the whole
    registry by it: ``upsert_organizer`` updates the existing profile rather
    than adding a second one, and two rows for one account would make
    "is this organizer suspended?" answerable two ways.
    """

    __tablename__ = "organizer_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(40), index=True)
    area_id: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, index=True)
    organization_id: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)  # the admin who set them up
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("user_id", name="uq_organizer_profile_user"),)


class TournamentStaffRow(Base):
    """An umpire or commentator on one competition's staff.

    Unique on (tournament, user, role) because that triple is the in-memory
    repository's key: re-adding somebody who was stood down reinstates their
    entry instead of creating a second, conflicting one — and with two rows,
    ``set_active`` would leave a stale "active" copy behind.
    """

    __tablename__ = "tournament_staff"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tournament_id: Mapped[str] = mapped_column(String(40), index=True)
    user_id: Mapped[str] = mapped_column(String(40), index=True)
    staff_role: Mapped[str] = mapped_column(String(20), index=True)  # umpire | commentator
    is_active: Mapped[bool] = mapped_column(default=True)
    added_by: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)  # the organizer who added them
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("tournament_id", "user_id", "staff_role", name="uq_tournament_staff"),
    )


class AuditLogRow(Base):
    """One append-only line of who changed what.

    ``created_at`` rather than the record's ``when``: ``when`` is a reserved
    word in SQL, and every other table here already dates its rows this way.
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_id: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(40), index=True)
    resource_type: Mapped[str] = mapped_column(String(30), default="", index=True)
    resource_id: Mapped[str] = mapped_column(String(40), default="", index=True)
    detail: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
