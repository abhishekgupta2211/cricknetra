"""Picture upload/serve — validates type and size, stores via the repository."""

from __future__ import annotations

from app.repositories.photo_repository import Photo, PhotoRepository

MAX_BYTES = 4 * 1024 * 1024  # 4 MB — plenty for a profile picture
ALLOWED_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}


class PhotoError(Exception):
    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class PhotoService:
    def __init__(self, photos: PhotoRepository) -> None:
        self.photos = photos

    def save(self, kind: str, owner_id: str, content_type: str | None, data: bytes) -> None:
        ct = (content_type or "").split(";")[0].strip().lower()
        if ct not in ALLOWED_TYPES:
            raise PhotoError("Please upload a PNG, JPG, WEBP or GIF image")
        if not data:
            raise PhotoError("The uploaded file is empty")
        if len(data) > MAX_BYTES:
            raise PhotoError("Image is too large — keep it under 4 MB")
        self.photos.set_photo(kind, owner_id, ct, data)

    def get(self, kind: str, owner_id: str) -> Photo | None:
        return self.photos.get_photo(kind, owner_id)

    def delete(self, kind: str, owner_id: str) -> None:
        self.photos.delete_photo(kind, owner_id)

    def has(self, kind: str, owner_id: str) -> bool:
        return self.photos.has_photo(kind, owner_id)

    def present(self, kind: str, owner_ids: list[str]) -> set[str]:
        return self.photos.owners_with_photos(kind, owner_ids)
