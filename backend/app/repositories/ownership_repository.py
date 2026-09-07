"""Resource ownership registry.

A tiny side-table that records who created each match / team / tournament,
without touching those entities' own models or repositories. ``owner`` is the
user id (string). A missing owner means "unowned" (e.g. data created before auth)
— only admins / capability-holders can mutate those.
"""

from __future__ import annotations

from typing import Optional, Protocol


class OwnershipRepository(Protocol):
    def set_owner(self, resource_type: str, resource_id: str, owner_id: str) -> None: ...
    def get_owner(self, resource_type: str, resource_id: str) -> Optional[str]: ...
    def delete(self, resource_type: str, resource_id: str) -> None: ...
    def count_by_owner(self, owner_id: str, resource_type: str) -> int: ...
    def list_by_owner(self, owner_id: str, resource_type: str) -> list[str]: ...


class InMemoryOwnershipRepository:
    def __init__(self) -> None:
        self._owners: dict[tuple[str, str], str] = {}

    def set_owner(self, resource_type, resource_id, owner_id) -> None:
        self._owners[(resource_type, str(resource_id))] = str(owner_id)

    def get_owner(self, resource_type, resource_id) -> Optional[str]:
        return self._owners.get((resource_type, str(resource_id)))

    def delete(self, resource_type, resource_id) -> None:
        self._owners.pop((resource_type, str(resource_id)), None)

    def count_by_owner(self, owner_id, resource_type) -> int:
        return sum(
            1 for (rt, _rid), owner in self._owners.items()
            if rt == resource_type and owner == str(owner_id)
        )

    def list_by_owner(self, owner_id, resource_type) -> list[str]:
        return [
            rid for (rt, rid), owner in self._owners.items()
            if rt == resource_type and owner == str(owner_id)
        ]
