"""Community / social service — follow graph, activity feed, notifications.

Following someone notifies them; an activity by a user notifies their followers
and shows up in their followers' feed.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.core import webpush
from app.core.config import settings
from app.repositories.social_repository import ActivityItem, NotificationItem, SocialRepository
from app.repositories.user_repository import UserRecord, UserRepository
from app.schemas.social import FollowState
from app.services import email_service, push_service


class SocialError(Exception):
    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


ENTITY_TYPES = {"team", "player", "tournament", "match", "club", "academy"}

# admin announcements go out under one of these categories (each respects its pref opt-out)
ANNOUNCE_CATEGORIES = {"system", "marketing"}

# derive a category (for icon/filtering) when an older notification has none stored
_CATEGORY_FOR_KIND = {
    "follow": "social", "activity": "social", "message": "social",
    "role": "system", "official": "system", "system": "system",
    "match": "match", "tournament": "tournament", "team": "team",
    "player": "player", "achievement": "achievement", "admin": "admin",
}


def category_for(kind: str, category: str = "") -> str:
    return category or _CATEGORY_FOR_KIND.get(kind, "social")


class SocialService:
    def __init__(self, social: SocialRepository, users: UserRepository) -> None:
        self.social = social
        self.users = users

    # ----- smart delivery: quiet hours (DND) + push gating -----
    @staticmethod
    def _in_quiet_hours(prefs: dict, now: "datetime | None" = None) -> bool:
        """True if the user's local time is inside their quiet window. The window is
        two local hours (0-23) and may wrap past midnight (e.g. 22 → 7)."""
        qs, qe = prefs.get("quiet_start"), prefs.get("quiet_end")
        if qs is None or qe is None or qs == qe:
            return False
        now = now or datetime.now(timezone.utc)
        local_h = int((now.hour * 60 + now.minute + (prefs.get("tz_offset") or 0)) // 60) % 24
        return qs <= local_h < qe if qs < qe else (local_h >= qs or local_h < qe)

    @staticmethod
    def _app_url(link: str) -> str:
        """Absolute URL for a notification email, from an in-app hash link (`#/match/9`)."""
        base = settings.app_base_url.rstrip("/")
        if link.startswith("#"):
            return f"{base}/app/{link}" if base else f"/app/{link}"
        return link or (f"{base}/app/" if base else "/app/")

    def _deliver_channels(self, user_id: str, prefs: dict, *, title: str, body: str,
                          link: str, tag: str, category: str, email: bool = False) -> None:
        """Fan a notification out to the user's live channels — push always, email when the
        producer marks it email-worthy AND the user opted in. Quiet hours mute the ping, not
        the stored in-app record (which the caller has already written)."""
        if self._in_quiet_hours(prefs):
            return
        if prefs.get("push_enabled", True):
            push_service.send_to_user(self.social, user_id, title=title, body=body,
                                      link=link, tag=tag, category=category)
        if email and prefs.get("email_enabled", False):
            user = self.users.get_by_id(str(user_id))
            addr = getattr(user, "email", None) if user else None
            if addr:
                text = f"{body}\n\nOpen CricNetra: {self._app_url(link)}" if link else body
                email_service.send(addr, title, text)

    # ----- follow -----
    def follow(self, follower: UserRecord, followee_id: str) -> FollowState:
        if str(follower.id) == str(followee_id):
            raise SocialError("You can't follow yourself")
        target = self.users.get_by_id(str(followee_id))
        if target is None:
            raise SocialError("User not found", 404)
        if not self.social.is_following(follower.id, followee_id):
            self.social.follow(follower.id, followee_id)
            link = f"#/u/{follower.id}"
            gkey = f"follow:{followee_id}"
            found = self.social.coalesce_unread(followee_id, gkey)
            if found:
                # a burst of new followers folds into one unread row (and doesn't re-ping)
                n = found[1] + 1
                others = n - 1
                text = f"{follower.username} and {others} other{'s' if others > 1 else ''} started following you"
                self.social.bump_notification(found[0], text=text, title="New followers",
                                              data={"count": n, "last": follower.username})
            else:
                text = f"{follower.username} started following you"
                self.social.add_notification(followee_id, "follow", text, link, category="social",
                                             title="New follower", data={"count": 1, "last": follower.username},
                                             group_key=gkey)
                prefs = self.social.get_prefs(followee_id)
                if prefs.get("social", True):
                    self._deliver_channels(followee_id, prefs, title="New follower", body=text,
                                           link=link, tag=gkey, category="social")
        return self.state(follower.id, followee_id)

    def unfollow(self, follower: UserRecord, followee_id: str) -> FollowState:
        self.social.unfollow(follower.id, followee_id)
        return self.state(follower.id, followee_id)

    def state(self, viewer_id: str, target_id: str) -> FollowState:
        followers, following = self.social.follow_counts(target_id)
        return FollowState(
            is_following=self.social.is_following(viewer_id, target_id),
            followers=followers, following=following,
        )

    def following_ids(self, user_id: str) -> list[str]:
        return self.social.following_ids(user_id)

    # ----- feed -----
    def feed(self, user_id: str, limit: int = 50) -> list[ActivityItem]:
        actors = self.social.following_ids(user_id) + [str(user_id)]  # own + followed
        return self.social.feed(actors, limit)

    def record(self, actor: UserRecord, kind: str, text: str, link: str = "") -> None:
        """Log an activity and notify the actor's followers."""
        self.social.add_activity(actor.id, actor.username, kind, text, link)
        for follower_id in self.social.follower_ids(actor.id):
            self.social.add_notification(follower_id, "activity", f"{actor.username} {text}", link)

    # ----- notifications -----
    def notifications(self, user_id: str, limit: int = 50) -> list[NotificationItem]:
        items = self.social.notifications(user_id, limit)
        for it in items:  # backfill a category on older rows so the UI can filter/icon them
            it.category = category_for(it.kind, it.category)
        return items

    def unread(self, user_id: str) -> int:
        return self.social.unread_count(user_id)

    def mark_read(self, user_id: str) -> None:
        self.social.mark_read(user_id)

    def delete_notification(self, user_id: str, notification_id: str) -> bool:
        return self.social.delete_notification(user_id, notification_id)

    def notification_version(self, user_id: str) -> tuple:
        """(unread, max_id) — cheap fingerprint for the realtime SSE gate."""
        return self.social.notification_version(user_id)

    # ----- entity follow (team / player / tournament / match / club / academy) -----
    def follow_entity(self, user: UserRecord, entity_type: str, entity_id: str) -> dict:
        if entity_type not in ENTITY_TYPES:
            raise SocialError(f"can't follow a '{entity_type}'")
        self.social.follow_entity(user.id, entity_type, entity_id)
        return self.entity_follow_state(user.id, entity_type, entity_id)

    def unfollow_entity(self, user: UserRecord, entity_type: str, entity_id: str) -> dict:
        self.social.unfollow_entity(user.id, entity_type, entity_id)
        return self.entity_follow_state(user.id, entity_type, entity_id)

    def entity_follow_state(self, user_id: str, entity_type: str, entity_id: str) -> dict:
        followers = self.social.entity_followers(entity_type, entity_id)
        return {
            "is_following": self.social.is_following_entity(user_id, entity_type, entity_id),
            "followers": len(followers),
        }

    def followed_entities(self, user_id: str, entity_type: "str | None" = None) -> list[dict]:
        return [{"entity_type": t, "entity_id": i}
                for (t, i) in self.social.followed_entities(user_id, entity_type)]

    # ----- fan-out to an entity's followers (respecting each user's prefs) -----
    def notify_followers(self, entity_type: str, entity_id: str, *, category: str, kind: str,
                         text: str, link: str = "", title: "str | None" = None,
                         data: "dict | None" = None, exclude: "str | None" = None,
                         group: "str | None" = None) -> int:
        """Notify everyone following an entity. When ``group`` is set, a fresh burst of
        the same group folds into one unread row per follower (and doesn't re-ping)."""
        sent = 0
        for follower_id in self.social.entity_followers(entity_type, entity_id):
            if exclude is not None and str(follower_id) == str(exclude):
                continue
            prefs = self.social.get_prefs(follower_id)
            if not prefs.get(category, True):  # category opt-out
                continue
            if group:
                found = self.social.coalesce_unread(follower_id, group)
                if found:
                    d = dict(data or {}); d["count"] = found[1] + 1
                    self.social.bump_notification(found[0], text=text, title=title, data=d)
                    sent += 1
                    continue  # coalesced → no re-ping
            d = dict(data or {}); d.setdefault("count", 1)
            self.social.add_notification(
                follower_id, kind, text, link, category=category, title=title,
                entity_type=entity_type, entity_id=str(entity_id), data=d, group_key=group,
            )
            self._deliver_channels(follower_id, prefs, title=title or "CricNetra", body=text,
                                   link=link, tag=group or f"{entity_type}:{entity_id}", category=category)
            sent += 1
        return sent

    def notify_user(self, user_id: str, *, category: str, kind: str, text: str, link: str = "",
                    title: "str | None" = None, data: "dict | None" = None,
                    group: "str | None" = None) -> bool:
        """Deliver one notification directly to a single user (e.g. an award they won).
        Honours their category pref, quiet hours and coalescing, like notify_followers."""
        prefs = self.social.get_prefs(user_id)
        if not prefs.get(category, True):
            return False
        if group:
            found = self.social.coalesce_unread(user_id, group)
            if found:
                d = dict(data or {}); d["count"] = found[1] + 1
                self.social.bump_notification(found[0], text=text, title=title, data=d)
                return True
        d = dict(data or {}); d.setdefault("count", 1)
        self.social.add_notification(user_id, kind, text, link, category=category, title=title,
                                     data=d, group_key=group)
        # a direct, personal notification (an award, a message) is email-worthy
        self._deliver_channels(user_id, prefs, title=title or "CricNetra", body=text,
                               link=link, tag=group or f"{kind}:{user_id}", category=category, email=True)
        return True

    # ----- preferences -----
    def get_prefs(self, user_id: str) -> dict:
        return self.social.get_prefs(user_id)

    def set_prefs(self, user_id: str, prefs: dict) -> dict:
        return self.social.set_prefs(user_id, prefs)

    # ----- web-push subscriptions -----
    def push_config(self) -> dict:
        """What the browser needs to subscribe: the app-server key + availability."""
        return {"key": webpush.application_server_key(), "available": webpush.available()}

    def add_push_subscription(self, user_id: str, endpoint: str, p256dh: str, auth: str,
                              platform: str = "web") -> None:
        self.social.add_subscription(user_id, endpoint, p256dh, auth, platform)

    def remove_push_subscription(self, user_id: str, endpoint: str) -> bool:
        # scope to the owner so one user can't drop another's device
        return self.social.delete_subscription(endpoint, user_id)

    def remove_all_push_subscriptions(self, user_id: str) -> int:
        return self.social.delete_subscriptions_for_user(user_id)

    def rotate_push_subscription(self, old_endpoint: "str | None", endpoint: str,
                                 p256dh: str, auth: str, platform: str = "web") -> bool:
        """Move a subscription to a new endpoint after the browser rotates it.

        Identity is the old endpoint itself (secret + unguessable); we only rotate
        one that already exists, and keep it under the same owner."""
        owner = self.social.subscription_owner(old_endpoint) if old_endpoint else None
        if owner is None:
            return False
        if old_endpoint and old_endpoint != endpoint:
            self.social.delete_subscription(old_endpoint)
        self.social.add_subscription(owner, endpoint, p256dh, auth, platform)
        return True

    # ----- admin broadcast announcements + engagement analytics -----
    def broadcast(self, admin: UserRecord, *, title: str, text: str, category: str = "system",
                  link: str = "") -> dict:
        """Fan an announcement out to every active user (in-app + push + email), honouring
        each user's category opt-out, and record it as a campaign for CTR analytics."""
        if category not in ANNOUNCE_CATEGORIES:
            raise SocialError(f"announcements must be {' or '.join(sorted(ANNOUNCE_CATEGORIES))}")
        users = self.users.list_users()
        targets = [(u, p) for u in users for p in [self.social.get_prefs(u.id)] if p.get(category, True)]
        campaign_id = self.social.record_announcement(
            title, text, category, link, admin.id, "all", len(targets))
        for u, prefs in targets:
            self.social.add_notification(
                u.id, "admin", text, link, category=category, title=title,
                data={"count": 1, "announcement": campaign_id}, campaign_id=campaign_id)
            self._deliver_channels(u.id, prefs, title=title, body=text, link=link,
                                   tag=f"campaign:{campaign_id}", category=category, email=True)
        return {"campaign_id": campaign_id, "recipients": len(targets), "audience": len(users)}

    def mark_clicked(self, user_id: str, notification_id: str) -> bool:
        return self.social.mark_clicked(user_id, notification_id)

    def announcement_analytics(self) -> list[dict]:
        """Per-campaign engagement: delivered / opened / clicked + open-rate + CTR."""
        counts = self.social.campaign_counts()
        out = []
        for a in self.social.list_announcements():
            d, o, cl = counts.get(a.id, (0, 0, 0))
            out.append({
                "id": a.id, "title": a.title, "text": a.text, "category": a.category,
                "link": a.link, "recipients": a.recipients, "when": a.when,
                "delivered": d, "opened": o, "clicked": cl,
                "open_rate": round(o / d, 4) if d else 0.0,
                "ctr": round(cl / d, 4) if d else 0.0,
            })
        return out
