"""Direct-messaging service. Any active user can message any other active user;
each new message drops a notification on the recipient (reusing the bell)."""

from __future__ import annotations

from app.repositories.messaging_repository import MessagingRepository
from app.repositories.social_repository import SocialRepository
from app.repositories.user_repository import UserRecord, UserRepository
from app.schemas.messaging import ConversationDTO, MessageDTO, ThreadDTO


class MessagingError(Exception):
    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _display(u: UserRecord | None, fallback: str = "Unknown") -> str:
    if u is None:
        return fallback
    return u.full_name or u.username or fallback


class MessagingService:
    def __init__(self, messaging: MessagingRepository, users: UserRepository, social: SocialRepository) -> None:
        self.msg = messaging
        self.users = users
        self.social = social

    def send(self, sender: UserRecord, recipient_id: str, text: str) -> MessageDTO:
        text = (text or "").strip()
        if not text:
            raise MessagingError("Message can't be empty")
        if str(recipient_id) == str(sender.id):
            raise MessagingError("You can't message yourself")
        recipient = self.users.get_by_id(str(recipient_id))
        if recipient is None or not getattr(recipient, "is_active", True):
            raise MessagingError("User not found", 404)
        item = self.msg.send(sender.id, recipient_id, text)
        # let the recipient know — links straight to the thread with the sender
        self.social.add_notification(
            recipient_id, "message",
            f"{_display(sender)} sent you a message", f"#/messages/{sender.id}",
        )
        return MessageDTO(**item.__dict__, mine=True)

    def conversations(self, me: UserRecord) -> list[ConversationDTO]:
        out = []
        for c in self.msg.conversations(me.id):
            other = self.users.get_by_id(c.other_id)
            out.append(ConversationDTO(
                other_id=c.other_id, other_name=_display(other),
                last_text=c.last_text, last_when=c.last_when,
                last_mine=(str(c.last_sender_id) == str(me.id)), unread=c.unread,
            ))
        return out

    def thread(self, me: UserRecord, other_id: str) -> ThreadDTO:
        other = self.users.get_by_id(str(other_id))
        if other is None:
            raise MessagingError("User not found", 404)
        self.msg.mark_thread_read(me.id, other_id)  # opening a thread reads it
        msgs = [
            MessageDTO(**m.__dict__, mine=(str(m.sender_id) == str(me.id)))
            for m in self.msg.thread(me.id, other_id)
        ]
        return ThreadDTO(other_id=str(other_id), other_name=_display(other), messages=msgs)

    def unread_total(self, user_id: str) -> int:
        return self.msg.unread_total(user_id)
