"""Community / social store — the follow graph, the activity feed, and
notifications, behind one repository (in-memory + SQL impls).

Kept as a single repo because the three concerns are small and always used
together by ``SocialService``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# per-user notification preferences: category toggles + delivery channels + the
# quiet-hours (DND) window, the in-app sound, and the client's UTC→local offset.
DEFAULT_PREFS: dict = {
    "match": True, "tournament": True, "team": True, "player": True, "social": True,
    "system": True, "achievement": True, "marketing": False,
    "email_enabled": False, "push_enabled": True, "sound": True,
    "quiet_start": None, "quiet_end": None, "tz_offset": 0,
}


@dataclass
class ActivityItem:
    id: str
    actor_id: str
    actor_name: str
    kind: str
    text: str
    link: str
    when: str  # ISO timestamp


@dataclass
class NotificationItem:
    id: str
    kind: str
    text: str
    link: str
    is_read: bool
    when: str
    category: str = ""
    title: str = ""
    count: int = 1        # how many events folded into this one (coalescing)


@dataclass
class AnnouncementItem:
    id: str
    title: str
    text: str
    category: str
    link: str
    created_by: str
    audience: str
    recipients: int
    when: str


@dataclass
class PushSubscription:
    endpoint: str
    p256dh: str
    auth: str

    def to_info(self) -> dict:
        """Shape pywebpush expects: {endpoint, keys:{p256dh, auth}}."""
        return {"endpoint": self.endpoint, "keys": {"p256dh": self.p256dh, "auth": self.auth}}


class SocialRepository(Protocol):
    # follow graph
    def follow(self, follower_id: str, followee_id: str) -> None: ...
    def unfollow(self, follower_id: str, followee_id: str) -> None: ...
    def is_following(self, follower_id: str, followee_id: str) -> bool: ...
    def following_ids(self, user_id: str) -> list[str]: ...
    def follower_ids(self, user_id: str) -> list[str]: ...
    def follow_counts(self, user_id: str) -> tuple[int, int]: ...  # (followers, following)
    # entity follow graph (user -> team|player|tournament|match|club|academy)
    def follow_entity(self, follower_id: str, entity_type: str, entity_id: str) -> None: ...
    def unfollow_entity(self, follower_id: str, entity_type: str, entity_id: str) -> None: ...
    def is_following_entity(self, follower_id: str, entity_type: str, entity_id: str) -> bool: ...
    def entity_followers(self, entity_type: str, entity_id: str) -> list[str]: ...
    def followed_entities(self, follower_id: str, entity_type: "str | None" = None) -> list[tuple[str, str]]: ...
    # activity feed
    def add_activity(self, actor_id: str, actor_name: str, kind: str, text: str, link: str) -> None: ...
    def feed(self, actor_ids: list[str], limit: int = 50) -> list[ActivityItem]: ...
    # notifications
    def add_notification(self, user_id: str, kind: str, text: str, link: str, *,
                         category: "str | None" = None, title: "str | None" = None,
                         entity_type: "str | None" = None, entity_id: "str | None" = None,
                         data: "dict | None" = None, group_key: "str | None" = None,
                         campaign_id: "str | None" = None) -> None: ...
    def coalesce_unread(self, user_id: str, group_key: str) -> "tuple[str, int] | None": ...  # (id, count)
    def bump_notification(self, notification_id: str, *, text: str, title: "str | None" = None,
                          data: "dict | None" = None) -> None: ...
    def notifications(self, user_id: str, limit: int = 50) -> list[NotificationItem]: ...
    def unread_count(self, user_id: str) -> int: ...
    def mark_read(self, user_id: str) -> None: ...
    def mark_clicked(self, user_id: str, notification_id: str) -> bool: ...
    def delete_notification(self, user_id: str, notification_id: str) -> bool: ...
    def notification_version(self, user_id: str) -> tuple: ...  # (unread, max_id) — SSE gate
    # admin announcements (broadcast campaigns) + their engagement funnel
    def record_announcement(self, title: str, text: str, category: str, link: str,
                            created_by: str, audience: str, recipients: int) -> str: ...
    def list_announcements(self, limit: int = 50) -> list[AnnouncementItem]: ...
    def campaign_counts(self) -> "dict[str, tuple[int, int, int]]": ...  # campaign_id -> (delivered, opened, clicked)
    # preferences
    def get_prefs(self, user_id: str) -> dict: ...
    def set_prefs(self, user_id: str, prefs: dict) -> dict: ...
    # web-push subscriptions (one row per browser/device endpoint)
    def add_subscription(self, user_id: str, endpoint: str, p256dh: str, auth: str,
                         platform: str = "web") -> None: ...
    def subscriptions_for_user(self, user_id: str) -> list[PushSubscription]: ...
    def subscription_owner(self, endpoint: str) -> "str | None": ...
    def delete_subscription(self, endpoint: str, user_id: "str | None" = None) -> bool: ...
    def delete_subscriptions_for_user(self, user_id: str) -> int: ...


class InMemorySocialRepository:
    def __init__(self) -> None:
        self._follows: set[tuple[str, str]] = set()
        self._entity_follows: set[tuple[str, str, str]] = set()  # (follower, entity_type, entity_id)
        self._prefs: dict[str, dict] = {}
        self._acts: list[dict] = []
        self._notes: list[dict] = []
        self._subs: list[dict] = []  # web-push subscriptions
        self._anns: list[dict] = []  # admin announcement campaigns
        self._seq = 0
        self._ann_seq = 0

    # ----- entity follow graph -----
    def follow_entity(self, follower_id, entity_type, entity_id) -> None:
        self._entity_follows.add((str(follower_id), entity_type, str(entity_id)))

    def unfollow_entity(self, follower_id, entity_type, entity_id) -> None:
        self._entity_follows.discard((str(follower_id), entity_type, str(entity_id)))

    def is_following_entity(self, follower_id, entity_type, entity_id) -> bool:
        return (str(follower_id), entity_type, str(entity_id)) in self._entity_follows

    def entity_followers(self, entity_type, entity_id) -> list[str]:
        return [f for (f, t, i) in self._entity_follows if t == entity_type and i == str(entity_id)]

    def followed_entities(self, follower_id, entity_type=None) -> list[tuple[str, str]]:
        return [(t, i) for (f, t, i) in self._entity_follows
                if f == str(follower_id) and (entity_type is None or t == entity_type)]

    # ----- preferences -----
    def get_prefs(self, user_id) -> dict:
        return dict(DEFAULT_PREFS, **self._prefs.get(str(user_id), {}))

    def set_prefs(self, user_id, prefs) -> dict:
        cur = self.get_prefs(user_id)
        cur.update({k: v for k, v in prefs.items() if k in DEFAULT_PREFS})
        self._prefs[str(user_id)] = cur
        return cur

    # ----- follow graph -----
    def follow(self, follower_id, followee_id) -> None:
        if str(follower_id) != str(followee_id):
            self._follows.add((str(follower_id), str(followee_id)))

    def unfollow(self, follower_id, followee_id) -> None:
        self._follows.discard((str(follower_id), str(followee_id)))

    def is_following(self, follower_id, followee_id) -> bool:
        return (str(follower_id), str(followee_id)) in self._follows

    def following_ids(self, user_id) -> list[str]:
        return [b for (a, b) in self._follows if a == str(user_id)]

    def follower_ids(self, user_id) -> list[str]:
        return [a for (a, b) in self._follows if b == str(user_id)]

    def follow_counts(self, user_id) -> tuple[int, int]:
        return (len(self.follower_ids(user_id)), len(self.following_ids(user_id)))

    # ----- activity feed -----
    def add_activity(self, actor_id, actor_name, kind, text, link) -> None:
        self._seq += 1
        self._acts.append({
            "id": str(self._seq), "actor_id": str(actor_id), "actor_name": actor_name,
            "kind": kind, "text": text, "link": link, "when": _now(),
        })

    def feed(self, actor_ids, limit=50) -> list[ActivityItem]:
        ids = {str(a) for a in actor_ids}
        items = [a for a in reversed(self._acts) if a["actor_id"] in ids][:limit]
        return [ActivityItem(a["id"], a["actor_id"], a["actor_name"], a["kind"], a["text"], a["link"], a["when"]) for a in items]

    # ----- notifications -----
    def add_notification(self, user_id, kind, text, link, *, category=None, title=None,
                         entity_type=None, entity_id=None, data=None, group_key=None,
                         campaign_id=None) -> None:
        self._seq += 1
        self._notes.append({
            "id": str(self._seq), "user_id": str(user_id), "kind": kind,
            "text": text, "link": link, "is_read": False, "when": _now(),
            "category": category or "", "title": title or "",
            "entity_type": entity_type, "entity_id": entity_id, "data": data,
            "group_key": group_key, "campaign_id": campaign_id,
            "opened_at": None, "clicked_at": None,
        })

    def coalesce_unread(self, user_id, group_key) -> "tuple[str, int] | None":
        for n in reversed(self._notes):  # newest first
            if (n["user_id"] == str(user_id) and n.get("group_key") == group_key
                    and not n["is_read"]):
                count = (n.get("data") or {}).get("count", 1)
                return (n["id"], int(count))
        return None

    def bump_notification(self, notification_id, *, text, title=None, data=None) -> None:
        for n in self._notes:
            if n["id"] == str(notification_id):
                n["text"] = text
                if title is not None:
                    n["title"] = title
                if data is not None:
                    n["data"] = data
                n["when"] = _now()      # resurface as the latest activity
                return

    def notifications(self, user_id, limit=50) -> list[NotificationItem]:
        items = [n for n in reversed(self._notes) if n["user_id"] == str(user_id)][:limit]
        return [NotificationItem(n["id"], n["kind"], n["text"], n["link"], n["is_read"], n["when"],
                                 n.get("category", ""), n.get("title", ""),
                                 int((n.get("data") or {}).get("count", 1))) for n in items]

    def unread_count(self, user_id) -> int:
        return sum(1 for n in self._notes if n["user_id"] == str(user_id) and not n["is_read"])

    def notification_version(self, user_id) -> tuple:
        mine = [n for n in self._notes if n["user_id"] == str(user_id)]
        return (sum(1 for n in mine if not n["is_read"]), max((int(n["id"]) for n in mine), default=0))

    def mark_read(self, user_id) -> None:
        for n in self._notes:
            if n["user_id"] == str(user_id):
                if not n["is_read"] and not n.get("opened_at"):
                    n["opened_at"] = _now()      # reading it counts as "opened" (funnel)
                n["is_read"] = True

    def mark_clicked(self, user_id, notification_id) -> bool:
        for n in self._notes:
            if n["id"] == str(notification_id) and n["user_id"] == str(user_id):
                if not n.get("clicked_at"):
                    n["clicked_at"] = _now()
                if not n.get("opened_at"):
                    n["opened_at"] = _now()      # a click implies it was seen
                n["is_read"] = True
                return True
        return False

    def delete_notification(self, user_id, notification_id) -> bool:
        before = len(self._notes)
        # only the recipient can delete their own notification
        self._notes = [
            n for n in self._notes
            if not (n["id"] == str(notification_id) and n["user_id"] == str(user_id))
        ]
        return len(self._notes) < before

    # ----- admin announcements + engagement funnel -----
    def record_announcement(self, title, text, category, link, created_by, audience, recipients) -> str:
        self._ann_seq += 1
        self._anns.append({
            "id": str(self._ann_seq), "title": title, "text": text, "category": category,
            "link": link, "created_by": str(created_by), "audience": audience,
            "recipients": int(recipients), "when": _now(),
        })
        return str(self._ann_seq)

    def list_announcements(self, limit=50) -> list[AnnouncementItem]:
        return [AnnouncementItem(a["id"], a["title"], a["text"], a["category"], a["link"],
                                 a["created_by"], a["audience"], a["recipients"], a["when"])
                for a in reversed(self._anns)][:limit]

    def campaign_counts(self) -> "dict[str, tuple[int, int, int]]":
        out: dict[str, list[int]] = {}
        for n in self._notes:
            cid = n.get("campaign_id")
            if not cid:
                continue
            agg = out.setdefault(cid, [0, 0, 0])
            agg[0] += 1                                   # delivered
            agg[1] += 1 if n.get("opened_at") else 0      # opened
            agg[2] += 1 if n.get("clicked_at") else 0     # clicked
        return {k: (v[0], v[1], v[2]) for k, v in out.items()}

    # ----- web-push subscriptions -----
    def add_subscription(self, user_id, endpoint, p256dh, auth, platform="web") -> None:
        # endpoint is the unique key: re-subscribing updates keys + owner (upsert).
        for s in self._subs:
            if s["endpoint"] == endpoint:
                s.update(user_id=str(user_id), p256dh=p256dh, auth=auth, platform=platform)
                return
        self._subs.append({
            "user_id": str(user_id), "endpoint": endpoint,
            "p256dh": p256dh, "auth": auth, "platform": platform,
        })

    def subscriptions_for_user(self, user_id) -> list[PushSubscription]:
        return [PushSubscription(s["endpoint"], s["p256dh"], s["auth"])
                for s in self._subs if s["user_id"] == str(user_id)]

    def subscription_owner(self, endpoint) -> "str | None":
        for s in self._subs:
            if s["endpoint"] == endpoint:
                return s["user_id"]
        return None

    def delete_subscription(self, endpoint, user_id=None) -> bool:
        before = len(self._subs)
        self._subs = [
            s for s in self._subs
            if not (s["endpoint"] == endpoint and (user_id is None or s["user_id"] == str(user_id)))
        ]
        return len(self._subs) < before

    def delete_subscriptions_for_user(self, user_id) -> int:
        before = len(self._subs)
        self._subs = [s for s in self._subs if s["user_id"] != str(user_id)]
        return before - len(self._subs)
