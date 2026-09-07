"""Per-match umpire approvals — an umpire may score a match only once the match's
owner (organizer) has approved their request to officiate it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class OfficialItem:
    umpire_id: str
    umpire_name: str
    status: str  # pending | approved


class MatchOfficialRepository(Protocol):
    def request(self, match_id: str, umpire_id: str, umpire_name: str) -> None: ...
    def set_status(self, match_id: str, umpire_id: str, status: str) -> bool: ...
    def remove(self, match_id: str, umpire_id: str) -> bool: ...
    def is_approved(self, match_id: str, umpire_id: str) -> bool: ...
    def status_for(self, match_id: str, umpire_id: str) -> str: ...  # none|pending|approved
    def list_for_match(self, match_id: str) -> list[OfficialItem]: ...
    def delete_for_match(self, match_id: str) -> None: ...  # the match is gone; so are its approvals


class InMemoryMatchOfficialRepository:
    def __init__(self) -> None:
        self._d: dict[tuple[str, str], dict] = {}  # (match_id, umpire_id) -> row

    def request(self, match_id, umpire_id, umpire_name) -> None:
        key = (str(match_id), str(umpire_id))
        if key not in self._d:  # keep an existing approval/request as-is
            self._d[key] = {"umpire_name": umpire_name, "status": "pending"}

    def set_status(self, match_id, umpire_id, status) -> bool:
        row = self._d.get((str(match_id), str(umpire_id)))
        if row is None:
            return False
        row["status"] = status
        return True

    def remove(self, match_id, umpire_id) -> bool:
        return self._d.pop((str(match_id), str(umpire_id)), None) is not None

    def is_approved(self, match_id, umpire_id) -> bool:
        row = self._d.get((str(match_id), str(umpire_id)))
        return bool(row and row["status"] == "approved")

    def status_for(self, match_id, umpire_id) -> str:
        row = self._d.get((str(match_id), str(umpire_id)))
        return row["status"] if row else "none"

    def list_for_match(self, match_id) -> list[OfficialItem]:
        return [
            OfficialItem(uid, row["umpire_name"], row["status"])
            for (mid, uid), row in self._d.items() if mid == str(match_id)
        ]

    def delete_for_match(self, match_id) -> None:
        """Drop every approval on a deleted match.

        An approval is a standing permission to score. Leaving one behind means
        a row that says an umpire may officiate a match that no longer exists —
        and, once ids are reused, on whatever match inherits the id.
        """
        for key in [k for k in self._d if k[0] == str(match_id)]:
            self._d.pop(key, None)
