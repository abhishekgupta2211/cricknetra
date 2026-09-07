"""Profile / player pictures — service validation + API upload/serve/delete.

The API client runs as the default admin (id "0"), so player and own-profile
photo flows are fully exercisable end-to-end.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.photo_repository import InMemoryPhotoRepository
from app.services.photo_service import MAX_BYTES, PhotoError, PhotoService

client = TestClient(app)

PNG = ("p.png", b"\x89PNG\r\nfake-bytes", "image/png")


# ----- service-level --------------------------------------------------------
def _svc():
    return PhotoService(InMemoryPhotoRepository())


def test_save_get_delete_roundtrip():
    svc = _svc()
    svc.save("player", "7", "image/png", b"abc")
    photo = svc.get("player", "7")
    assert photo is not None and photo.data == b"abc" and photo.content_type == "image/png"
    assert svc.has("player", "7") is True
    assert svc.delete("player", "7") is None
    assert svc.get("player", "7") is None
    assert svc.has("player", "7") is False


def test_upload_replaces_previous():
    svc = _svc()
    svc.save("user", "1", "image/png", b"first")
    svc.save("user", "1", "image/jpeg", b"second")
    photo = svc.get("user", "1")
    assert photo.data == b"second" and photo.content_type == "image/jpeg"


def test_rejects_non_image_type():
    with pytest.raises(PhotoError):
        _svc().save("player", "1", "text/plain", b"hello")


def test_rejects_empty_and_oversized():
    svc = _svc()
    with pytest.raises(PhotoError):
        svc.save("player", "1", "image/png", b"")
    with pytest.raises(PhotoError):
        svc.save("player", "1", "image/png", b"x" * (MAX_BYTES + 1))


def test_present_batches_existence():
    svc = _svc()
    svc.save("player", "1", "image/png", b"a")
    svc.save("player", "3", "image/png", b"b")
    assert svc.present("player", ["1", "2", "3"]) == {"1", "3"}


# ----- API: player photo ----------------------------------------------------
def test_player_photo_upload_serve_flag_delete():
    pid = client.post("/api/v1/players", json={"name": "Pic Player"}).json()["id"]
    assert client.post(f"/api/v1/players/{pid}/photo", files={"file": PNG}).status_code == 204

    got = client.get(f"/api/v1/players/{pid}/photo")
    assert got.status_code == 200
    assert got.headers["content-type"].startswith("image/png")
    assert got.content == PNG[1]

    assert client.get(f"/api/v1/players/{pid}").json()["has_photo"] is True
    assert any(p["id"] == pid and p["has_photo"] for p in client.get("/api/v1/players").json())

    assert client.delete(f"/api/v1/players/{pid}/photo").status_code == 204
    assert client.get(f"/api/v1/players/{pid}/photo").status_code == 404
    assert client.get(f"/api/v1/players/{pid}").json()["has_photo"] is False


def test_player_photo_rejects_bad_type():
    pid = client.post("/api/v1/players", json={"name": "Bad Pic"}).json()["id"]
    r = client.post(f"/api/v1/players/{pid}/photo", files={"file": ("x.txt", b"nope", "text/plain")})
    assert r.status_code == 400


def test_player_photo_404_for_unknown_player():
    assert client.post("/api/v1/players/999999/photo", files={"file": PNG}).status_code == 404


# ----- API: team logo -------------------------------------------------------
def test_team_logo_upload_serve_flag_delete():
    tid = client.post("/api/v1/teams", json={"name": "Logo FC"}).json()["id"]
    assert client.post(f"/api/v1/teams/{tid}/photo", files={"file": PNG}).status_code == 204

    got = client.get(f"/api/v1/teams/{tid}/photo")
    assert got.status_code == 200 and got.content == PNG[1]
    assert client.get(f"/api/v1/teams/{tid}").json()["has_photo"] is True
    assert any(t["id"] == tid and t["has_photo"] for t in client.get("/api/v1/teams").json())

    assert client.delete(f"/api/v1/teams/{tid}/photo").status_code == 204
    assert client.get(f"/api/v1/teams/{tid}/photo").status_code == 404
    assert client.get(f"/api/v1/teams/{tid}").json()["has_photo"] is False


def test_team_member_carries_player_photo_flag():
    tid = client.post("/api/v1/teams", json={"name": "Squad SC"}).json()["id"]
    pid = client.post("/api/v1/players", json={"name": "Member M"}).json()["id"]
    client.post(f"/api/v1/teams/{tid}/members", json={"player_id": pid})
    client.post(f"/api/v1/players/{pid}/photo", files={"file": PNG})
    members = client.get(f"/api/v1/teams/{tid}").json()["members"]
    assert members[0]["has_photo"] is True


# ----- API: my profile photo ------------------------------------------------
def test_profile_photo_upload_serve_me_flag_delete():
    assert client.post("/api/v1/auth/profile/photo", files={"file": PNG}).status_code == 204
    # served publicly by user id (admin is "0")
    got = client.get("/api/v1/users/0/photo")
    assert got.status_code == 200 and got.content == PNG[1]
    assert client.get("/api/v1/auth/me").json()["has_photo"] is True
    assert client.delete("/api/v1/auth/profile/photo").status_code == 204
    assert client.get("/api/v1/users/0/photo").status_code == 404
    assert client.get("/api/v1/auth/me").json()["has_photo"] is False
