"""Picture store — profile/player photos as bytes, behind one repository.

Keyed by ``(kind, owner_id)`` with at most one photo per owner (uploading again
replaces it). ``kind`` is "player" or "user".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class Photo:
    content_type: str
    data: bytes


class PhotoRepository(Protocol):
    def set_photo(self, kind: str, owner_id: str, content_type: str, data: bytes) -> None: ...
    def get_photo(self, kind: str, owner_id: str) -> Photo | None: ...
    def delete_photo(self, kind: str, owner_id: str) -> bool: ...
    def has_photo(self, kind: str, owner_id: str) -> bool: ...
    def owners_with_photos(self, kind: str, owner_ids: list[str]) -> set[str]: ...


class InMemoryPhotoRepository:
    def __init__(self) -> None:
        self._d: dict[tuple[str, str], Photo] = {}

    def set_photo(self, kind, owner_id, content_type, data) -> None:
        self._d[(kind, str(owner_id))] = Photo(content_type, data)

    def get_photo(self, kind, owner_id) -> Photo | None:
        return self._d.get((kind, str(owner_id)))

    def delete_photo(self, kind, owner_id) -> bool:
        return self._d.pop((kind, str(owner_id)), None) is not None

    def has_photo(self, kind, owner_id) -> bool:
        return (kind, str(owner_id)) in self._d

    def owners_with_photos(self, kind, owner_ids) -> set[str]:
        wanted = {str(x) for x in owner_ids}
        return {oid for (k, oid) in self._d if k == kind and oid in wanted}
