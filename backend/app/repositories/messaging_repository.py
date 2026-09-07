"""Direct 1:1 messages between users (in-memory + SQL impls).

A "conversation" isn't a stored entity — it's derived from messages sharing a
canonical ``pair_key`` (the two participant ids, sorted), so listing threads and
fetching a thread are both single indexed lookups.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Protocol


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def pair_key(a: str, b: str) -> str:
    x, y = sorted([str(a), str(b)])
    return f"{x}:{y}"


@dataclass
class MessageItem:
    id: str
    sender_id: str
    recipient_id: str
    text: str
    is_read: bool
    when: str


@dataclass
class ConversationItem:
    other_id: str
    last_text: str
    last_when: str
    last_sender_id: str  # who sent the most recent message (to label "You: …")
    unread: int


class MessagingRepository(Protocol):
    def send(self, sender_id: str, recipient_id: str, text: str) -> MessageItem: ...
    def thread(self, user_id: str, other_id: str, limit: int = 100) -> list[MessageItem]: ...
    def conversations(self, user_id: str) -> list[ConversationItem]: ...
    def mark_thread_read(self, user_id: str, other_id: str) -> None: ...
    def unread_total(self, user_id: str) -> int: ...


class InMemoryMessagingRepository:
    def __init__(self) -> None:
        self._msgs: list[dict] = []
        self._seq = 0

    def send(self, sender_id, recipient_id, text) -> MessageItem:
        self._seq += 1
        m = {
            "id": str(self._seq), "pair": pair_key(sender_id, recipient_id),
            "sender_id": str(sender_id), "recipient_id": str(recipient_id),
            "text": text, "is_read": False, "when": _now(),
        }
        self._msgs.append(m)
        return MessageItem(m["id"], m["sender_id"], m["recipient_id"], m["text"], m["is_read"], m["when"])

    def thread(self, user_id, other_id, limit=100) -> list[MessageItem]:
        pk = pair_key(user_id, other_id)
        items = [m for m in self._msgs if m["pair"] == pk][-limit:]  # oldest → newest
        return [MessageItem(m["id"], m["sender_id"], m["recipient_id"], m["text"], m["is_read"], m["when"]) for m in items]

    def conversations(self, user_id) -> list[ConversationItem]:
        uid = str(user_id)
        latest: dict[str, dict] = {}
        unread: dict[str, int] = {}
        for m in self._msgs:  # insert order → last write per counterpart is newest
            if uid not in (m["sender_id"], m["recipient_id"]):
                continue
            other = m["recipient_id"] if m["sender_id"] == uid else m["sender_id"]
            latest[other] = m
            if m["recipient_id"] == uid and not m["is_read"]:
                unread[other] = unread.get(other, 0) + 1
        convos = [
            ConversationItem(other, m["text"], m["when"], m["sender_id"], unread.get(other, 0))
            for other, m in latest.items()
        ]
        convos.sort(key=lambda c: c.last_when, reverse=True)
        return convos

    def mark_thread_read(self, user_id, other_id) -> None:
        uid, oid = str(user_id), str(other_id)
        for m in self._msgs:
            if m["recipient_id"] == uid and m["sender_id"] == oid and not m["is_read"]:
                m["is_read"] = True

    def unread_total(self, user_id) -> int:
        uid = str(user_id)
        return sum(1 for m in self._msgs if m["recipient_id"] == uid and not m["is_read"])
