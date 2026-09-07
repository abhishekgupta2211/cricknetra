"""FastAPI dependencies.

Shared services are injected everywhere. Repositories are built lazily as
singletons and chosen from settings (database vs in-memory). The match and stats
services share the same match + match-player repositories so stats see the same
data the match service writes.
"""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.services.scope_service import ScopeError, ScopeService
from app.core.permissions import Caps, Roles, has_capability, is_admin
from app.core.security import JWTError, decode_access_token
from app.repositories.match_player_repository import (
    InMemoryMatchPlayerRepository,
    MatchPlayerRepository,
)
from app.repositories.member_activity_repository import (
    InMemoryMemberActivityRepository,
    MemberActivityRepository,
)
from app.repositories.ownership_repository import (
    InMemoryOwnershipRepository,
    OwnershipRepository,
)
from app.repositories.user_repository import (
    InMemoryUserRepository,
    UserRecord,
    UserRepository,
)
from app.services.auth_service import AuthService
from app.services.profile_service import ProfileService
from app.repositories.match_repository import InMemoryMatchRepository, MatchRepository
from app.repositories.roster_repository import InMemoryRosterRepository, RosterRepository
from app.repositories.rule_template_repository import (
    InMemoryRuleTemplateRepository,
    RuleTemplateRepository,
)
from app.repositories.tournament_repository import (
    InMemoryTournamentRepository,
    TournamentRepository,
)
from app.repositories.tournament_squad_repository import (
    InMemoryTournamentSquadRepository,
    TournamentSquadRepository,
)
from app.services.match_service import MatchService
from app.services.roster_service import RosterService
from app.services.rule_template_service import RuleTemplateService
from app.services.stats_service import StatsService
from app.services.tournament_service import TournamentService

_match_repo: Optional[MatchRepository] = None
_match_player_repo: Optional[MatchPlayerRepository] = None
_roster_repo: Optional[RosterRepository] = None
_rule_template_repo: Optional[RuleTemplateRepository] = None
_tournament_repo: Optional[TournamentRepository] = None

_match_service: Optional[MatchService] = None
_stats_service: Optional[StatsService] = None
_roster_service: Optional[RosterService] = None
_rule_template_service: Optional[RuleTemplateService] = None
_tournament_service: Optional[TournamentService] = None


def _sql_sessionmaker():
    from app.db.session import get_sessionmaker, init_db

    init_db()
    return get_sessionmaker()


def _match_repo_singleton() -> MatchRepository:
    global _match_repo
    if _match_repo is None:
        if settings.database_url:
            from app.repositories.sql_match_repository import SqlMatchRepository

            _match_repo = SqlMatchRepository(_sql_sessionmaker())
        else:
            _match_repo = InMemoryMatchRepository()
    return _match_repo


def _match_player_repo_singleton() -> MatchPlayerRepository:
    global _match_player_repo
    if _match_player_repo is None:
        if settings.database_url:
            from app.repositories.sql_match_player_repository import SqlMatchPlayerRepository

            _match_player_repo = SqlMatchPlayerRepository(_sql_sessionmaker())
        else:
            _match_player_repo = InMemoryMatchPlayerRepository()
    return _match_player_repo


def _roster_repo_singleton() -> RosterRepository:
    global _roster_repo
    if _roster_repo is None:
        if settings.database_url:
            from app.repositories.sql_roster_repository import SqlRosterRepository

            _roster_repo = SqlRosterRepository(_sql_sessionmaker())
        else:
            _roster_repo = InMemoryRosterRepository()
    return _roster_repo


def _rule_template_repo_singleton() -> RuleTemplateRepository:
    global _rule_template_repo
    if _rule_template_repo is None:
        if settings.database_url:
            from app.repositories.sql_rule_template_repository import SqlRuleTemplateRepository

            _rule_template_repo = SqlRuleTemplateRepository(_sql_sessionmaker())
        else:
            _rule_template_repo = InMemoryRuleTemplateRepository()
    return _rule_template_repo


def get_match_service() -> MatchService:
    global _match_service
    if _match_service is None:
        _match_service = MatchService(_match_repo_singleton(), _match_player_repo_singleton())
    return _match_service


def get_clipper_service(match_service: MatchService = Depends(get_match_service)):
    """Auto highlight-clip generator (ffmpeg). Stateless over the match service.
    Takes it as a sub-dependency so test overrides of the repo are respected."""
    from app.services.clipper_service import ClipperService

    return ClipperService(match_service)


def get_stats_service() -> StatsService:
    global _stats_service
    if _stats_service is None:
        _stats_service = StatsService(
            _match_repo_singleton(), _match_player_repo_singleton(), _roster_repo_singleton(),
            _fielding_event_repo_singleton(),
        )
    return _stats_service


# --------------------------------------------------------------------------- #
# Fielding events (dropped catches / runs saved / misfields)
# --------------------------------------------------------------------------- #
_fielding_event_repo = None


def _fielding_event_repo_singleton():
    global _fielding_event_repo
    if _fielding_event_repo is None:
        if settings.database_url:
            from app.repositories.sql_fielding_event_repository import SqlFieldingEventRepository

            _fielding_event_repo = SqlFieldingEventRepository(_sql_sessionmaker())
        else:
            from app.repositories.fielding_event_repository import InMemoryFieldingEventRepository

            _fielding_event_repo = InMemoryFieldingEventRepository()
    return _fielding_event_repo


def get_fielding_event_service():
    from app.services.fielding_event_service import FieldingEventService

    return FieldingEventService(_fielding_event_repo_singleton())


# --------------------------------------------------------------------------- #
# Venues (grounds + coaching academies directory)
# --------------------------------------------------------------------------- #
_venue_repo = None


def _venue_repo_singleton():
    global _venue_repo
    if _venue_repo is None:
        if settings.database_url:
            from app.repositories.sql_venue_repository import SqlVenueRepository

            _venue_repo = SqlVenueRepository(_sql_sessionmaker())
        else:
            from app.repositories.venue_repository import InMemoryVenueRepository

            _venue_repo = InMemoryVenueRepository()
    return _venue_repo


def get_venue_service():
    from app.services.venue_service import VenueService

    return VenueService(_venue_repo_singleton())


def get_roster_service() -> RosterService:
    global _roster_service
    if _roster_service is None:
        _roster_service = RosterService(_roster_repo_singleton())
    return _roster_service


def _tournament_repo_singleton() -> TournamentRepository:
    global _tournament_repo
    if _tournament_repo is None:
        if settings.database_url:
            from app.repositories.sql_tournament_repository import SqlTournamentRepository

            _tournament_repo = SqlTournamentRepository(_sql_sessionmaker())
        else:
            _tournament_repo = InMemoryTournamentRepository()
    return _tournament_repo


def get_rule_template_service() -> RuleTemplateService:
    global _rule_template_service
    if _rule_template_service is None:
        _rule_template_service = RuleTemplateService(_rule_template_repo_singleton())
    return _rule_template_service


_tournament_squad_repo: Optional[TournamentSquadRepository] = None


def _tournament_squad_repo_singleton() -> TournamentSquadRepository:
    global _tournament_squad_repo
    if _tournament_squad_repo is None:
        if settings.database_url:
            from app.repositories.sql_tournament_squad_repository import SqlTournamentSquadRepository

            _tournament_squad_repo = SqlTournamentSquadRepository(_sql_sessionmaker())
        else:
            _tournament_squad_repo = InMemoryTournamentSquadRepository()
    return _tournament_squad_repo


def get_tournament_service() -> TournamentService:
    global _tournament_service
    if _tournament_service is None:
        _tournament_service = TournamentService(
            _tournament_repo_singleton(), get_match_service(), get_roster_service(),
            _tournament_squad_repo_singleton(),
        )
    return _tournament_service


# --------------------------------------------------------------------------- #
# Auth — user repository, services, and the current-user dependency
# --------------------------------------------------------------------------- #
_user_repo: Optional[UserRepository] = None
_auth_service: Optional[AuthService] = None
_profile_service: Optional[ProfileService] = None


def _user_repo_singleton() -> UserRepository:
    global _user_repo
    if _user_repo is None:
        if settings.database_url:
            from app.repositories.sql_user_repository import SqlUserRepository

            _user_repo = SqlUserRepository(_sql_sessionmaker())
        else:
            _user_repo = InMemoryUserRepository()
            _maybe_seed_admin(_user_repo)
    return _user_repo


def _maybe_seed_admin(repo: UserRepository) -> None:
    """Seed one admin into the in-memory store when ``CRICNETRA_SEED_ADMIN`` is set
    (format ``username:password``). For local/e2e use only: the SQL path never calls
    this, so production — which always configures a database url — is unaffected."""
    import os

    spec = os.environ.get("CRICNETRA_SEED_ADMIN")
    if not spec or ":" not in spec:
        return
    username, _, password = spec.partition(":")
    username = username.strip().lower()
    if not username or not password or repo.get_by_username(username) is not None:
        return
    from app.core.security import hash_password

    repo.add_user(
        full_name="Seed Admin", username=username, mobile_no="9999999999",
        password_hash=hash_password(password), role="admin",
    )


def get_user_repo() -> UserRepository:
    return _user_repo_singleton()


def get_auth_service() -> AuthService:
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService(
            _user_repo_singleton(), _role_request_repo_singleton(), _auth_token_repo_singleton()
        )
    return _auth_service


# --------------------------------------------------------------------------- #
# Elevated-role approval (pending requests granted by an admin)
# --------------------------------------------------------------------------- #
_role_request_repo = None


def _role_request_repo_singleton():
    global _role_request_repo
    if _role_request_repo is None:
        if settings.database_url:
            from app.repositories.sql_role_request_repository import SqlRoleRequestRepository

            _role_request_repo = SqlRoleRequestRepository(_sql_sessionmaker())
        else:
            from app.repositories.role_request_repository import InMemoryRoleRequestRepository

            _role_request_repo = InMemoryRoleRequestRepository()
    return _role_request_repo


def get_role_request_repo():
    return _role_request_repo_singleton()


def get_role_service():
    from app.services.role_service import RoleService

    return RoleService(_user_repo_singleton(), _role_request_repo_singleton(), _social_repo_singleton())


def get_profile_service() -> ProfileService:
    global _profile_service
    if _profile_service is None:
        _profile_service = ProfileService(_user_repo_singleton())
    return _profile_service


# --------------------------------------------------------------------------- #
# Account verification + password reset (short-lived tokens)
# --------------------------------------------------------------------------- #
_auth_token_repo = None


def _auth_token_repo_singleton():
    global _auth_token_repo
    if _auth_token_repo is None:
        if settings.database_url:
            from app.repositories.sql_auth_token_repository import SqlAuthTokenRepository

            _auth_token_repo = SqlAuthTokenRepository(_sql_sessionmaker())
        else:
            from app.repositories.auth_token_repository import InMemoryAuthTokenRepository

            _auth_token_repo = InMemoryAuthTokenRepository()
    return _auth_token_repo


def get_account_service():
    from app.core.notifications import build_notifier
    from app.services.account_service import AccountService

    return AccountService(_user_repo_singleton(), _auth_token_repo_singleton(), build_notifier())


# Extracts the Bearer token from the Authorization header. auto_error=False so we
# raise our own consistent 401 (tokenUrl is only used by the /docs "Authorize" UI).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    repo: UserRepository = Depends(get_user_repo),
) -> UserRecord:
    if not token:
        raise _CREDENTIALS_EXC
    try:
        payload = decode_access_token(token)
    except JWTError:
        raise _CREDENTIALS_EXC
    user_id = payload.get("sub")
    if user_id is None:
        raise _CREDENTIALS_EXC
    user = repo.get_by_id(str(user_id))
    if user is None:
        raise _CREDENTIALS_EXC
    return user


def get_current_active_user(user: UserRecord = Depends(get_current_user)) -> UserRecord:
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")
    return user


def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    repo: UserRepository = Depends(get_user_repo),
) -> Optional[UserRecord]:
    """Like get_current_user but returns None instead of 401 — for endpoints that
    are public but show extra data to signed-in members (e.g. search)."""
    if not token:
        return None
    try:
        payload = decode_access_token(token)
    except JWTError:
        return None
    user_id = payload.get("sub")
    if user_id is None:
        return None
    return repo.get_by_id(str(user_id))


def require_roles(*roles: str):
    """Dependency factory: only allow users whose role is in ``roles``."""

    def _dep(user: UserRecord = Depends(get_current_active_user)) -> UserRecord:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return user

    return _dep


# --------------------------------------------------------------------------- #
# Capabilities + ownership (role-based authorization)
# --------------------------------------------------------------------------- #
_ownership_repo: Optional[OwnershipRepository] = None


def _ownership_repo_singleton() -> OwnershipRepository:
    global _ownership_repo
    if _ownership_repo is None:
        if settings.database_url:
            from app.repositories.sql_ownership_repository import SqlOwnershipRepository

            _ownership_repo = SqlOwnershipRepository(_sql_sessionmaker())
        else:
            _ownership_repo = InMemoryOwnershipRepository()
    return _ownership_repo


def get_ownership_repo() -> OwnershipRepository:
    return _ownership_repo_singleton()


# Per-match umpire approvals — the repo getter lives here because require_match_scorer
# (below) depends on it; the service getter is defined later (it also needs social).
_match_official_repo = None


def _match_official_repo_singleton():
    global _match_official_repo
    if _match_official_repo is None:
        if settings.database_url:
            from app.repositories.sql_match_official_repository import SqlMatchOfficialRepository

            _match_official_repo = SqlMatchOfficialRepository(_sql_sessionmaker())
        else:
            from app.repositories.match_official_repository import InMemoryMatchOfficialRepository

            _match_official_repo = InMemoryMatchOfficialRepository()
    return _match_official_repo


def get_match_official_repo():
    return _match_official_repo_singleton()


# Organizers, and the areas / organizations they run competitions for.
_org_repo = None


def _org_repo_singleton():
    """Chosen from settings like every other repository.

    It was unconditionally in-memory, which on a multi-worker Postgres
    deployment meant an organizer appointed on one process did not exist on the
    next — and ScopeService refuses an organizer whose profile it cannot see.
    """
    global _org_repo
    if _org_repo is None:
        if settings.database_url:
            from app.repositories.sql_org_repository import SqlOrgRepository

            _org_repo = SqlOrgRepository(_sql_sessionmaker())
        else:
            from app.repositories.org_repository import InMemoryOrgRepository

            _org_repo = InMemoryOrgRepository()
    return _org_repo


def get_org_repo():
    return _org_repo_singleton()


def get_tournament_repo() -> TournamentRepository:
    return _tournament_repo_singleton()


# Umpires and commentators an organizer runs a competition with.
_staff_repo = None


def _staff_repo_singleton():
    """Chosen from settings like every other repository. Authorization reads
    this on every request that opens a competition's working view, so a
    process-local copy let an umpire onto their tournament on one worker and
    told them they were not on it from the next."""
    global _staff_repo
    if _staff_repo is None:
        if settings.database_url:
            from app.repositories.sql_tournament_staff_repository import (
                SqlTournamentStaffRepository,
            )

            _staff_repo = SqlTournamentStaffRepository(_sql_sessionmaker())
        else:
            from app.repositories.tournament_staff_repository import (
                InMemoryTournamentStaffRepository,
            )

            _staff_repo = InMemoryTournamentStaffRepository()
    return _staff_repo


def get_staff_repo():
    return _staff_repo_singleton()


# Who changed what — roles granted, competitions deleted.
_audit_repo = None


def _audit_repo_singleton():
    """Chosen from settings like every other repository.

    The sharpest case of the three: the trail exists to answer "who granted
    that role" and "who deleted that competition" weeks after the fact, and an
    in-memory trail answers both with silence after the next deploy.
    """
    global _audit_repo
    if _audit_repo is None:
        if settings.database_url:
            from app.repositories.sql_audit_repository import SqlAuditRepository

            _audit_repo = SqlAuditRepository(_sql_sessionmaker())
        else:
            from app.repositories.audit_repository import InMemoryAuditRepository

            _audit_repo = InMemoryAuditRepository()
    return _audit_repo


def get_audit_repo():
    return _audit_repo_singleton()


def get_scope_service(
    owners: OwnershipRepository = Depends(get_ownership_repo),
    tournaments: TournamentRepository = Depends(get_tournament_repo),
    staff=Depends(get_staff_repo),
    officials=Depends(get_match_official_repo),
    orgs=Depends(get_org_repo),
) -> ScopeService:
    """The one place ownership and scope are decided.

    Takes its stores through Depends rather than reaching for the singletons,
    so a test (or any other composition) that swaps a repository is actually
    honoured — reading the singleton directly made this guard authorize
    against a different ownership store than the one the routes wrote to.
    """
    return ScopeService(
        owners=owners,
        tournaments=tournaments,
        staff=staff,
        officials=officials,
        orgs=orgs,
    )


def require_admin(user: UserRecord = Depends(get_current_active_user)) -> UserRecord:
    """Admin-only endpoints (deleting resources, approving roles)."""
    if not is_admin(user.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


def require_capability(cap: str):
    """Dependency factory: the current user's role must grant ``cap``."""

    def _dep(user: UserRecord = Depends(get_current_active_user)) -> UserRecord:
        if not has_capability(user.role, cap):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Your role ('{user.role}') is not allowed to do this.",
            )
        return user

    return _dep


def _authorize_mutation(user: UserRecord, owner_id: Optional[str], cap: Optional[str] = None) -> None:
    """Allow if admin, the owner, or (optionally) a capability-holder. Else 403."""
    if is_admin(user.role):
        return
    if owner_id is not None and str(owner_id) == str(user.id):
        return
    if cap is not None and has_capability(user.role, cap):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You don't have permission to modify this resource.",
    )


def require_match_scorer(
    match_id: str,
    user: UserRecord = Depends(get_current_active_user),
    scope: ScopeService = Depends(get_scope_service),
) -> UserRecord:
    """Score a match: the admin, whoever started it, the organizer whose
    competition it belongs to, or an umpire approved for *this* match.

    Note what is NOT here: holding SCORE_MATCH. Every organizer holds it, so
    accepting it alone let one organizer score another's fixtures by changing
    the id in the URL.
    """
    try:
        scope.require_score(user, match_id)
    except ScopeError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    return user


def require_match_owner(
    match_id: str,
    user: UserRecord = Depends(get_current_active_user),
    scope: ScopeService = Depends(get_scope_service),
) -> UserRecord:
    """Edit or delete a match — narrower than scoring. An assigned umpire may
    score a match without being allowed to delete it."""
    try:
        scope.require_manage_match(user, match_id)
    except ScopeError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    return user


def require_team_owner(
    team_id: str,
    user: UserRecord = Depends(get_current_active_user),
    owners: OwnershipRepository = Depends(get_ownership_repo),
) -> UserRecord:
    _authorize_mutation(user, owners.get_owner("team", team_id))
    return user


def require_tournament_owner(
    tournament_id: str,
    user: UserRecord = Depends(get_current_active_user),
    scope: ScopeService = Depends(get_scope_service),
) -> UserRecord:
    """Manage a competition: the admin, or the organizer who owns it. One
    organizer must never reach another's tournament by guessing its id."""
    try:
        scope.require_tournament(user, tournament_id, cap=Caps.MANAGE_TOURNAMENT)
    except ScopeError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    return user


def require_tournament_staffer(
    tournament_id: str,
    user: UserRecord = Depends(get_current_active_user),
    scope: ScopeService = Depends(get_scope_service),
) -> UserRecord:
    """Open a competition's working view: its organizer, or an umpire or
    commentator assigned to it. Read-only for the staff."""
    try:
        scope.require_workspace(user, tournament_id)
    except ScopeError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    return user


def require_organizer(
    user: UserRecord = Depends(get_current_active_user),
    scope: ScopeService = Depends(get_scope_service),
) -> UserRecord:
    """An active organizer (or the admin). A deactivated organizer keeps the
    role but loses the ability to act, without needing to be demoted."""
    try:
        scope.require_active_organizer(user)
    except ScopeError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    return user


# --------------------------------------------------------------------------- #
# Member records (activity tallies shown in the Network directory / account)
# --------------------------------------------------------------------------- #
_activity_repo: Optional[MemberActivityRepository] = None


def _activity_repo_singleton() -> MemberActivityRepository:
    global _activity_repo
    if _activity_repo is None:
        if settings.database_url:
            from app.repositories.sql_member_activity_repository import SqlMemberActivityRepository

            _activity_repo = SqlMemberActivityRepository(_sql_sessionmaker())
        else:
            _activity_repo = InMemoryMemberActivityRepository()
    return _activity_repo


def get_activity_repo() -> MemberActivityRepository:
    return _activity_repo_singleton()


# --------------------------------------------------------------------------- #
# Community / social (follow graph, activity feed, notifications)
# --------------------------------------------------------------------------- #
_social_repo = None


def _social_repo_singleton():
    global _social_repo
    if _social_repo is None:
        if settings.database_url:
            from app.repositories.sql_social_repository import SqlSocialRepository

            _social_repo = SqlSocialRepository(_sql_sessionmaker())
        else:
            from app.repositories.social_repository import InMemorySocialRepository

            _social_repo = InMemorySocialRepository()
    return _social_repo


def get_social_repo():
    return _social_repo_singleton()


def get_social_service():
    from app.services.social_service import SocialService

    return SocialService(_social_repo_singleton(), _user_repo_singleton())


# --------------------------------------------------------------------------- #
# Match awards (MoM / best batter / best bowler), persisted per match
# --------------------------------------------------------------------------- #
_award_repo = None


def _award_repo_singleton():
    global _award_repo
    if _award_repo is None:
        if settings.database_url:
            from app.repositories.sql_award_repository import SqlAwardRepository

            _award_repo = SqlAwardRepository(_sql_sessionmaker())
        else:
            from app.repositories.award_repository import InMemoryAwardRepository

            _award_repo = InMemoryAwardRepository()
    return _award_repo


def get_award_repo():
    return _award_repo_singleton()


# --------------------------------------------------------------------------- #
# Notification producers (domain events → follower notifications)
# --------------------------------------------------------------------------- #
_notification_dispatcher = None


def get_notification_dispatcher():
    # A process-wide singleton so its idempotency (fired milestones / finished matches)
    # persists across the per-ball requests. Tests override it with a fresh instance.
    global _notification_dispatcher
    if _notification_dispatcher is None:
        from app.services.notification_generators import NotificationDispatcher

        _notification_dispatcher = NotificationDispatcher(
            get_social_service(),
            awards=_award_repo_singleton(),
            roster=_roster_repo_singleton(),
            match_players=_match_player_repo_singleton(),
            tournaments=_tournament_repo_singleton(),
        )
    return _notification_dispatcher


# --------------------------------------------------------------------------- #
# Direct messages + the "Looking For" board
# --------------------------------------------------------------------------- #
_messaging_repo = None
_looking_for_repo = None


def _messaging_repo_singleton():
    global _messaging_repo
    if _messaging_repo is None:
        if settings.database_url:
            from app.repositories.sql_messaging_repository import SqlMessagingRepository

            _messaging_repo = SqlMessagingRepository(_sql_sessionmaker())
        else:
            from app.repositories.messaging_repository import InMemoryMessagingRepository

            _messaging_repo = InMemoryMessagingRepository()
    return _messaging_repo


def get_messaging_service():
    from app.services.messaging_service import MessagingService

    return MessagingService(_messaging_repo_singleton(), _user_repo_singleton(), _social_repo_singleton())


def _looking_for_repo_singleton():
    global _looking_for_repo
    if _looking_for_repo is None:
        if settings.database_url:
            from app.repositories.sql_looking_for_repository import SqlLookingForRepository

            _looking_for_repo = SqlLookingForRepository(_sql_sessionmaker())
        else:
            from app.repositories.looking_for_repository import InMemoryLookingForRepository

            _looking_for_repo = InMemoryLookingForRepository()
    return _looking_for_repo


def get_looking_for_service():
    from app.services.looking_for_service import LookingForService

    return LookingForService(_looking_for_repo_singleton())


# --------------------------------------------------------------------------- #
# Pictures (profile / player photos)
# --------------------------------------------------------------------------- #
_photo_repo = None


def _photo_repo_singleton():
    global _photo_repo
    if _photo_repo is None:
        if settings.database_url:
            from app.repositories.sql_photo_repository import SqlPhotoRepository

            _photo_repo = SqlPhotoRepository(_sql_sessionmaker())
        else:
            from app.repositories.photo_repository import InMemoryPhotoRepository

            _photo_repo = InMemoryPhotoRepository()
    return _photo_repo


def get_photo_repo():
    return _photo_repo_singleton()


def get_photo_service():
    from app.services.photo_service import PhotoService

    return PhotoService(_photo_repo_singleton())


# --------------------------------------------------------------------------- #
# Match commentary
# --------------------------------------------------------------------------- #
_commentary_repo = None


def _commentary_repo_singleton():
    global _commentary_repo
    if _commentary_repo is None:
        if settings.database_url:
            from app.repositories.sql_commentary_repository import SqlCommentaryRepository

            _commentary_repo = SqlCommentaryRepository(_sql_sessionmaker())
        else:
            from app.repositories.commentary_repository import InMemoryCommentaryRepository

            _commentary_repo = InMemoryCommentaryRepository()
    return _commentary_repo


def get_commentary_service():
    from app.services.commentary_service import CommentaryService

    return CommentaryService(_commentary_repo_singleton())


def get_match_official_service():
    from app.services.match_official_service import MatchOfficialService

    return MatchOfficialService(
        _match_official_repo_singleton(), _ownership_repo_singleton(), _social_repo_singleton()
    )


def member_records(
    user_id: str, owners: OwnershipRepository, activity: MemberActivityRepository
):
    """Build a member's records: owned counts from the ownership registry, and
    umpired/commentated from the activity registry."""
    from app.schemas.user import MemberRecords

    return MemberRecords(
        matches_scored=owners.count_by_owner(user_id, "match"),
        tournaments_organized=owners.count_by_owner(user_id, "tournament"),
        teams_owned=owners.count_by_owner(user_id, "team"),
        matches_umpired=activity.count(user_id, "match_umpired"),
        matches_commentated=activity.count(user_id, "match_commentated"),
    )


# --------------------------------------------------------------------------- #
# Admin: areas / organizations / organizers, and the audit trail
# --------------------------------------------------------------------------- #
def get_audit_service(
    audit=Depends(get_audit_repo),
    users: UserRepository = Depends(get_user_repo),
):
    """The audit trail. Takes its stores through Depends (like get_scope_service)
    so a test that swaps the user repo sees its own actors resolved."""
    from app.services.audit_service import AuditService

    return AuditService(audit, users)


def get_org_service(
    orgs=Depends(get_org_repo),
    users: UserRepository = Depends(get_user_repo),
    owners: OwnershipRepository = Depends(get_ownership_repo),
    audit=Depends(get_audit_service),
):
    """Areas, organizations, organizers and role assignment.

    The ownership repo comes in because an organizer's tournament count is read
    from it — and because standing an organizer down must leave those rows
    alone, which is easier to keep honest with the store in plain sight.
    """
    from app.services.org_service import OrgService

    return OrgService(orgs=orgs, users=users, owners=owners, audit=audit)


# --------------------------------------------------------------------------- #
# Tournament staff — an organizer's umpires and commentators, per competition
# --------------------------------------------------------------------------- #
def get_staff_service(
    staff=Depends(get_staff_repo),
    users: UserRepository = Depends(get_user_repo),
    tournaments: TournamentService = Depends(get_tournament_service),
    audit=Depends(get_audit_service),
):
    """Umpires and commentators, scoped to one tournament.

    The tournament *repository* is taken off the tournament service rather than
    from its own singleton for the same reason get_scope_service takes its
    stores through Depends: a test (or any other composition) that swaps the
    service must not leave this reading a different set of competitions than
    the routes write to.
    """
    from app.services.staff_service import StaffService

    return StaffService(
        staff=staff,
        users=users,
        tournaments=tournaments.repo,
        audit=audit,
    )
