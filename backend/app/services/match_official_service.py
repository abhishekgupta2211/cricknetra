"""Per-match umpire approvals — request to officiate, owner approves/declines."""

from __future__ import annotations

from app.repositories.match_official_repository import MatchOfficialRepository, OfficialItem
from app.repositories.ownership_repository import OwnershipRepository


class MatchOfficialService:
    def __init__(self, officials: MatchOfficialRepository, owners: OwnershipRepository, social=None) -> None:
        self.officials = officials
        self.owners = owners
        self.social = social  # optional social repo (add_notification)

    def request(self, umpire, match_id: str) -> None:
        self.officials.request(match_id, umpire.id, umpire.full_name or umpire.username)
        owner = self.owners.get_owner("match", match_id)
        if owner and self.social:
            self.social.add_notification(
                owner, "official",
                f"{umpire.username} asked to officiate your match", f"#/match/{match_id}",
            )

    def approve(self, match_id: str, umpire_id: str) -> None:
        self.officials.set_status(match_id, umpire_id, "approved")
        if self.social:
            self.social.add_notification(
                umpire_id, "official",
                "You're approved to officiate a match 🎉", f"#/match/{match_id}",
            )

    def decline(self, match_id: str, umpire_id: str) -> None:
        self.officials.remove(match_id, umpire_id)
        if self.social:
            self.social.add_notification(
                umpire_id, "official",
                "Your request to officiate was declined", f"#/match/{match_id}",
            )

    def clear_match(self, match_id: str) -> None:
        """Forget every request and approval on a deleted match.

        An approval is a standing permission to score that match, so leaving
        one behind is an authorization row pointing at nothing — and at
        whatever match inherits the id if ids are ever reused.
        """
        self.officials.delete_for_match(match_id)

    def status_for(self, match_id: str, user_id: str) -> str:
        return self.officials.status_for(match_id, user_id)

    def list_for_match(self, match_id: str) -> list[OfficialItem]:
        return self.officials.list_for_match(match_id)
