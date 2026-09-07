"""Test isolation — fresh in-memory stores per test (no Postgres needed)."""

from __future__ import annotations

import pytest

from datetime import datetime, timezone

from app.api.deps import (
    get_account_service,
    get_activity_repo,
    get_audit_repo,
    get_auth_service,
    get_award_repo,
    get_commentary_service,
    get_current_active_user,
    get_current_user,
    get_fielding_event_service,
    get_looking_for_service,
    get_match_official_repo,
    get_match_official_service,
    get_match_service,
    get_messaging_service,
    get_notification_dispatcher,
    get_org_repo,
    get_ownership_repo,
    get_photo_service,
    get_profile_service,
    get_role_service,
    get_roster_service,
    get_rule_template_service,
    get_social_service,
    get_staff_repo,
    get_stats_service,
    get_tournament_repo,
    get_tournament_service,
    get_user_repo,
    get_venue_service,
)
from app.main import app
from app.repositories.award_repository import InMemoryAwardRepository
from app.repositories.match_player_repository import InMemoryMatchPlayerRepository
from app.repositories.match_repository import InMemoryMatchRepository
from app.repositories.auth_token_repository import InMemoryAuthTokenRepository
from app.repositories.commentary_repository import InMemoryCommentaryRepository
from app.repositories.match_official_repository import InMemoryMatchOfficialRepository
from app.repositories.member_activity_repository import InMemoryMemberActivityRepository
from app.repositories.audit_repository import InMemoryAuditRepository
from app.repositories.org_repository import InMemoryOrgRepository
from app.repositories.ownership_repository import InMemoryOwnershipRepository
from app.repositories.tournament_staff_repository import (
    InMemoryTournamentStaffRepository,
)
from app.repositories.photo_repository import InMemoryPhotoRepository
from app.repositories.role_request_repository import InMemoryRoleRequestRepository
from app.repositories.roster_repository import InMemoryRosterRepository
from app.repositories.rule_template_repository import InMemoryRuleTemplateRepository
from app.repositories.fielding_event_repository import InMemoryFieldingEventRepository
from app.repositories.looking_for_repository import InMemoryLookingForRepository
from app.repositories.messaging_repository import InMemoryMessagingRepository
from app.repositories.social_repository import InMemorySocialRepository
from app.repositories.tournament_repository import InMemoryTournamentRepository
from app.repositories.venue_repository import InMemoryVenueRepository
from app.repositories.tournament_squad_repository import InMemoryTournamentSquadRepository
from app.repositories.user_repository import InMemoryUserRepository, UserRecord
from app.services.account_service import AccountService
from app.services.auth_service import AuthService
from app.services.commentary_service import CommentaryService
from app.services.match_official_service import MatchOfficialService
from app.services.match_service import MatchService
from app.services.photo_service import PhotoService
from app.services.profile_service import ProfileService
from app.services.role_service import RoleService
from app.services.roster_service import RosterService
from app.services.rule_template_service import RuleTemplateService
from app.services.fielding_event_service import FieldingEventService
from app.services.looking_for_service import LookingForService
from app.services.messaging_service import MessagingService
from app.services.notification_generators import NotificationDispatcher
from app.services.social_service import SocialService
from app.services.stats_service import StatsService
from app.services.tournament_service import TournamentService
from app.services.venue_service import VenueService


@pytest.fixture(autouse=True)
def _in_memory_services():
    from app.core.config import settings as _settings
    _settings.rate_limit_enabled = False  # don't throttle the test client
    _settings.database_url = None  # in-memory everywhere; /health reports not_configured
    # Isolate tests from the developer's .env: codes come back in the response and
    # delivery stays on the console (never a real SMS/email provider).
    _settings.auth_dev_delivery = True
    _settings.smtp_host = None
    _settings.twilio_account_sid = None
    # match + stats services share one match repo and one match-player repo
    match_repo = InMemoryMatchRepository()
    mp_repo = InMemoryMatchPlayerRepository()
    roster_repo = InMemoryRosterRepository()
    org_repo = InMemoryOrgRepository()
    staff_repo = InMemoryTournamentStaffRepository()
    audit_repo = InMemoryAuditRepository()
    fielding_repo = InMemoryFieldingEventRepository()
    match_service = MatchService(match_repo, mp_repo)
    stats_service = StatsService(match_repo, mp_repo, roster_repo, fielding_repo)
    fielding_service = FieldingEventService(fielding_repo)
    roster_service = RosterService(roster_repo)
    rule_service = RuleTemplateService(InMemoryRuleTemplateRepository())
    tournament_repo = InMemoryTournamentRepository()
    tournament_service = TournamentService(
        tournament_repo, match_service, roster_service,
        InMemoryTournamentSquadRepository(),
    )
    # auth: one in-memory user repo shared by both services and get_current_user
    user_repo = InMemoryUserRepository()
    role_request_repo = InMemoryRoleRequestRepository()
    token_repo = InMemoryAuthTokenRepository()
    auth_service = AuthService(user_repo, role_request_repo, token_repo)
    account_service = AccountService(user_repo, token_repo)
    profile_service = ProfileService(user_repo)
    ownership_repo = InMemoryOwnershipRepository()
    activity_repo = InMemoryMemberActivityRepository()
    social_repo = InMemorySocialRepository()
    social_service = SocialService(social_repo, user_repo)
    award_repo = InMemoryAwardRepository()
    # a fresh dispatcher per test → its idempotency (fired milestones / finished matches)
    # starts empty, so producers can't leak across tests
    dispatcher = NotificationDispatcher(
        social_service, awards=award_repo, roster=roster_repo,
        match_players=mp_repo, tournaments=tournament_repo,
    )
    messaging_service = MessagingService(InMemoryMessagingRepository(), user_repo, social_repo)
    looking_for_service = LookingForService(InMemoryLookingForRepository())
    venue_service = VenueService(InMemoryVenueRepository())
    photo_service = PhotoService(InMemoryPhotoRepository())
    role_service = RoleService(user_repo, role_request_repo, social_repo)
    commentary_service = CommentaryService(InMemoryCommentaryRepository())
    official_repo = InMemoryMatchOfficialRepository()
    official_service = MatchOfficialService(official_repo, ownership_repo, social_repo)
    # Most tests aren't about auth — run them as a default admin so the gated
    # mutation endpoints behave as before. test_auth/test_permissions opt out.
    now = datetime.now(timezone.utc)
    admin = UserRecord(
        id="0", full_name="Test Admin", username="admin", mobile_no="0000000000",
        user_code="CN000000", role_code="ADM0000", password="", role="admin",
        is_active=True, is_verified=True, created_at=now, updated_at=now,
    )

    app.dependency_overrides[get_match_service] = lambda: match_service
    app.dependency_overrides[get_stats_service] = lambda: stats_service
    app.dependency_overrides[get_roster_service] = lambda: roster_service
    app.dependency_overrides[get_rule_template_service] = lambda: rule_service
    app.dependency_overrides[get_tournament_service] = lambda: tournament_service
    app.dependency_overrides[get_user_repo] = lambda: user_repo
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_account_service] = lambda: account_service
    app.dependency_overrides[get_profile_service] = lambda: profile_service
    app.dependency_overrides[get_ownership_repo] = lambda: ownership_repo
    app.dependency_overrides[get_org_repo] = lambda: org_repo
    app.dependency_overrides[get_staff_repo] = lambda: staff_repo
    app.dependency_overrides[get_audit_repo] = lambda: audit_repo
    app.dependency_overrides[get_tournament_repo] = lambda: tournament_repo
    app.dependency_overrides[get_activity_repo] = lambda: activity_repo
    app.dependency_overrides[get_social_service] = lambda: social_service
    app.dependency_overrides[get_award_repo] = lambda: award_repo
    app.dependency_overrides[get_notification_dispatcher] = lambda: dispatcher
    app.dependency_overrides[get_messaging_service] = lambda: messaging_service
    app.dependency_overrides[get_looking_for_service] = lambda: looking_for_service
    app.dependency_overrides[get_fielding_event_service] = lambda: fielding_service
    app.dependency_overrides[get_venue_service] = lambda: venue_service
    app.dependency_overrides[get_photo_service] = lambda: photo_service
    app.dependency_overrides[get_role_service] = lambda: role_service
    app.dependency_overrides[get_commentary_service] = lambda: commentary_service
    app.dependency_overrides[get_match_official_repo] = lambda: official_repo
    app.dependency_overrides[get_match_official_service] = lambda: official_service
    app.dependency_overrides[get_current_user] = lambda: admin
    app.dependency_overrides[get_current_active_user] = lambda: admin
    yield
    app.dependency_overrides.clear()
