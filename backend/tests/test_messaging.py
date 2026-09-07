"""Direct messages — service logic + API wiring (#140)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.messaging_repository import InMemoryMessagingRepository
from app.repositories.social_repository import InMemorySocialRepository
from app.repositories.user_repository import UserRecord
from app.services.messaging_service import MessagingError, MessagingService

client = TestClient(app)


def _user(uid: str, name: str) -> UserRecord:
    now = datetime.now(timezone.utc)
    return UserRecord(
        id=uid, full_name=name, username=name.lower(), mobile_no="9" + uid.rjust(9, "0"),
        user_code="CN" + uid.rjust(6, "0"), role_code="RC" + uid, password="",
        role="general_user", is_active=True, is_verified=True, created_at=now, updated_at=now,
    )


class _Users:
    def __init__(self, users):
        self._u = {str(u.id): u for u in users}

    def get_by_id(self, uid):
        return self._u.get(str(uid))


# ----- service logic --------------------------------------------------------
def test_send_thread_conversations_roundtrip():
    A, B = _user("1", "Alice"), _user("2", "Bob")
    social = InMemorySocialRepository()
    svc = MessagingService(InMemoryMessagingRepository(), _Users([A, B]), social)

    sent = svc.send(A, "2", "hi bob")
    assert sent.mine is True and sent.text == "hi bob"

    convos = svc.conversations(B)
    assert len(convos) == 1
    assert convos[0].other_id == "1" and convos[0].other_name == "Alice"
    assert convos[0].unread == 1 and convos[0].last_mine is False
    assert svc.unread_total("2") == 1

    th = svc.thread(B, "1")  # opening the thread marks it read
    assert th.other_name == "Alice" and len(th.messages) == 1
    assert th.messages[0].mine is False
    assert svc.unread_total("2") == 0

    assert any(n.kind == "message" for n in social.notifications("2"))

    ca = svc.conversations(A)
    assert ca[0].other_id == "2" and ca[0].last_mine is True and ca[0].unread == 0


def test_reply_orders_thread_for_both():
    A, B = _user("1", "Alice"), _user("2", "Bob")
    svc = MessagingService(InMemoryMessagingRepository(), _Users([A, B]), InMemorySocialRepository())
    svc.send(A, "2", "hi")
    svc.send(B, "1", "hey back")
    th = svc.thread(A, "2")
    assert [m.text for m in th.messages] == ["hi", "hey back"]
    assert [m.mine for m in th.messages] == [True, False]


def test_send_validation():
    A = _user("1", "Alice")
    svc = MessagingService(InMemoryMessagingRepository(), _Users([A]), InMemorySocialRepository())
    with pytest.raises(MessagingError) as self_err:
        svc.send(A, "1", "to self")
    assert self_err.value.status_code == 400
    with pytest.raises(MessagingError) as ghost_err:
        svc.send(A, "99", "ghost")
    assert ghost_err.value.status_code == 404
    with pytest.raises(MessagingError):
        svc.send(A, "2", "   ")  # empty after strip


# ----- API wiring (acting as the conftest default admin, id "0") ------------
def test_api_message_validation():
    assert client.post("/api/v1/messages", json={"recipient_id": "0", "text": "hi"}).status_code == 400
    assert client.post("/api/v1/messages", json={"recipient_id": "99999", "text": "hi"}).status_code == 404


def test_api_inbox_empty_and_unread_zero():
    assert client.get("/api/v1/messages").json() == []
    assert client.get("/api/v1/messages/unread").json() == {"count": 0}


def test_api_send_to_registered_user():
    reg = client.post("/api/v1/auth/register", json={
        "full_name": "Bob Msg", "username": "bobmsg140", "mobile_no": "9140000140",
        "password": "secret123", "role": "player",
    }).json()
    bid = str(reg["id"])
    r = client.post("/api/v1/messages", json={"recipient_id": bid, "text": "welcome!"})
    assert r.status_code == 201
    body = r.json()
    assert body["mine"] is True and body["text"] == "welcome!"

    inbox = client.get("/api/v1/messages").json()
    assert any(c["other_id"] == bid for c in inbox)

    th = client.get(f"/api/v1/messages/{bid}").json()
    assert th["other_id"] == bid and len(th["messages"]) == 1 and th["messages"][0]["mine"] is True
