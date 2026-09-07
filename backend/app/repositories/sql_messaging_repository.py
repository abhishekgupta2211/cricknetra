"""SQL-backed direct-messaging repository."""

from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import MessageRow
from app.repositories.messaging_repository import ConversationItem, MessageItem, pair_key


class SqlMessagingRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    def send(self, sender_id, recipient_id, text) -> MessageItem:
        with self._sf() as s:
            row = MessageRow(
                pair_key=pair_key(sender_id, recipient_id),
                sender_id=str(sender_id), recipient_id=str(recipient_id), text=text,
            )
            s.add(row)
            s.commit()
            s.refresh(row)
            return MessageItem(str(row.id), row.sender_id, row.recipient_id, row.text, row.is_read, row.created_at.isoformat())

    def thread(self, user_id, other_id, limit=100) -> list[MessageItem]:
        pk = pair_key(user_id, other_id)
        with self._sf() as s:
            rows = (
                s.query(MessageRow).filter_by(pair_key=pk)
                .order_by(MessageRow.id.desc()).limit(limit).all()
            )
            rows.reverse()  # back to oldest → newest
            return [MessageItem(str(r.id), r.sender_id, r.recipient_id, r.text, r.is_read, r.created_at.isoformat()) for r in rows]

    def conversations(self, user_id) -> list[ConversationItem]:
        uid = str(user_id)
        with self._sf() as s:
            rows = (
                s.query(MessageRow)
                .filter(or_(MessageRow.sender_id == uid, MessageRow.recipient_id == uid))
                .order_by(MessageRow.id.asc()).all()
            )
        latest: dict[str, MessageRow] = {}
        unread: dict[str, int] = {}
        for r in rows:
            other = r.recipient_id if r.sender_id == uid else r.sender_id
            latest[other] = r
            if r.recipient_id == uid and not r.is_read:
                unread[other] = unread.get(other, 0) + 1
        convos = [
            ConversationItem(other, r.text, r.created_at.isoformat(), r.sender_id, unread.get(other, 0))
            for other, r in latest.items()
        ]
        convos.sort(key=lambda c: c.last_when, reverse=True)
        return convos

    def mark_thread_read(self, user_id, other_id) -> None:
        with self._sf() as s:
            s.query(MessageRow).filter_by(
                recipient_id=str(user_id), sender_id=str(other_id), is_read=False
            ).update({"is_read": True})
            s.commit()

    def unread_total(self, user_id) -> int:
        with self._sf() as s:
            return (
                s.query(func.count(MessageRow.id))
                .filter_by(recipient_id=str(user_id), is_read=False).scalar() or 0
            )
