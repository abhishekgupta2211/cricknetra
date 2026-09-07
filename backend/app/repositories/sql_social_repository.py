"""SQL-backed community/social repository (follows, activity feed, notifications)."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import (
    ActivityRow,
    AnnouncementRow,
    EntityFollowRow,
    FollowRow,
    NotificationPrefRow,
    NotificationRow,
    PushSubscriptionRow,
)
from app.repositories.social_repository import (
    DEFAULT_PREFS,
    ActivityItem,
    AnnouncementItem,
    NotificationItem,
    PushSubscription,
)


class SqlSocialRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sf = session_factory

    # ----- follow graph -----
    def follow(self, follower_id, followee_id) -> None:
        if str(follower_id) == str(followee_id):
            return
        with self._sf() as s:
            if s.query(FollowRow.id).filter_by(follower_id=str(follower_id), followee_id=str(followee_id)).first():
                return
            s.add(FollowRow(follower_id=str(follower_id), followee_id=str(followee_id)))
            try:
                s.commit()
            except IntegrityError:
                s.rollback()

    def unfollow(self, follower_id, followee_id) -> None:
        with self._sf() as s:
            s.query(FollowRow).filter_by(follower_id=str(follower_id), followee_id=str(followee_id)).delete()
            s.commit()

    def is_following(self, follower_id, followee_id) -> bool:
        with self._sf() as s:
            return bool(
                s.query(FollowRow.id).filter_by(follower_id=str(follower_id), followee_id=str(followee_id)).first()
            )

    def following_ids(self, user_id) -> list[str]:
        with self._sf() as s:
            return [r[0] for r in s.query(FollowRow.followee_id).filter_by(follower_id=str(user_id)).all()]

    def follower_ids(self, user_id) -> list[str]:
        with self._sf() as s:
            return [r[0] for r in s.query(FollowRow.follower_id).filter_by(followee_id=str(user_id)).all()]

    def follow_counts(self, user_id) -> tuple[int, int]:
        with self._sf() as s:
            followers = s.query(func.count(FollowRow.id)).filter_by(followee_id=str(user_id)).scalar() or 0
            following = s.query(func.count(FollowRow.id)).filter_by(follower_id=str(user_id)).scalar() or 0
            return (followers, following)

    # ----- entity follow graph -----
    def follow_entity(self, follower_id, entity_type, entity_id) -> None:
        with self._sf() as s:
            if s.query(EntityFollowRow.id).filter_by(
                follower_id=str(follower_id), entity_type=entity_type, entity_id=str(entity_id)
            ).first():
                return
            s.add(EntityFollowRow(follower_id=str(follower_id), entity_type=entity_type, entity_id=str(entity_id)))
            try:
                s.commit()
            except IntegrityError:
                s.rollback()

    def unfollow_entity(self, follower_id, entity_type, entity_id) -> None:
        with self._sf() as s:
            s.query(EntityFollowRow).filter_by(
                follower_id=str(follower_id), entity_type=entity_type, entity_id=str(entity_id)
            ).delete()
            s.commit()

    def is_following_entity(self, follower_id, entity_type, entity_id) -> bool:
        with self._sf() as s:
            return bool(s.query(EntityFollowRow.id).filter_by(
                follower_id=str(follower_id), entity_type=entity_type, entity_id=str(entity_id)
            ).first())

    def entity_followers(self, entity_type, entity_id) -> list[str]:
        with self._sf() as s:
            return [r[0] for r in s.query(EntityFollowRow.follower_id).filter_by(
                entity_type=entity_type, entity_id=str(entity_id)).all()]

    def followed_entities(self, follower_id, entity_type=None) -> list[tuple[str, str]]:
        with self._sf() as s:
            q = s.query(EntityFollowRow.entity_type, EntityFollowRow.entity_id).filter_by(follower_id=str(follower_id))
            if entity_type is not None:
                q = q.filter(EntityFollowRow.entity_type == entity_type)
            return [(r[0], r[1]) for r in q.all()]

    # ----- preferences -----
    def get_prefs(self, user_id) -> dict:
        with self._sf() as s:
            row = s.get(NotificationPrefRow, str(user_id))
            return dict(DEFAULT_PREFS) if row is None else {k: getattr(row, k) for k in DEFAULT_PREFS}

    def set_prefs(self, user_id, prefs) -> dict:
        with self._sf() as s:
            row = s.get(NotificationPrefRow, str(user_id))
            if row is None:
                row = NotificationPrefRow(user_id=str(user_id))
                s.add(row)
            for k, v in prefs.items():
                if k in DEFAULT_PREFS:
                    setattr(row, k, v)
            s.commit()
            return {k: getattr(row, k) for k in DEFAULT_PREFS}

    # ----- activity feed -----
    def add_activity(self, actor_id, actor_name, kind, text, link) -> None:
        with self._sf() as s:
            s.add(ActivityRow(actor_id=str(actor_id), actor_name=actor_name, kind=kind, text=text, link=link or ""))
            s.commit()

    def feed(self, actor_ids, limit=50) -> list[ActivityItem]:
        ids = [str(a) for a in actor_ids]
        if not ids:
            return []
        with self._sf() as s:
            rows = (
                s.query(ActivityRow)
                .filter(ActivityRow.actor_id.in_(ids))
                .order_by(ActivityRow.id.desc())
                .limit(limit)
                .all()
            )
            return [
                ActivityItem(str(r.id), r.actor_id, r.actor_name, r.kind, r.text, r.link, r.created_at.isoformat())
                for r in rows
            ]

    # ----- notifications -----
    def add_notification(self, user_id, kind, text, link, *, category=None, title=None,
                         entity_type=None, entity_id=None, data=None, group_key=None,
                         campaign_id=None) -> None:
        with self._sf() as s:
            s.add(NotificationRow(
                user_id=str(user_id), kind=kind, text=text, link=link or "",
                category=category, title=title, entity_type=entity_type,
                entity_id=(str(entity_id) if entity_id is not None else None), data=data,
                group_key=group_key, campaign_id=campaign_id,
            ))
            s.commit()

    def coalesce_unread(self, user_id, group_key) -> "tuple[str, int] | None":
        with self._sf() as s:
            row = (
                s.query(NotificationRow)
                .filter_by(user_id=str(user_id), group_key=group_key, is_read=False)
                .order_by(NotificationRow.id.desc())
                .first()
            )
            if row is None:
                return None
            count = (row.data or {}).get("count", 1)
            return (str(row.id), int(count))

    def bump_notification(self, notification_id, *, text, title=None, data=None) -> None:
        try:
            nid = int(notification_id)
        except (TypeError, ValueError):
            return
        with self._sf() as s:
            row = s.get(NotificationRow, nid)
            if row is None:
                return
            row.text = text
            if title is not None:
                row.title = title
            if data is not None:
                row.data = data
            row.created_at = func.now()   # resurface as the latest activity
            s.commit()

    def notifications(self, user_id, limit=50) -> list[NotificationItem]:
        with self._sf() as s:
            rows = (
                s.query(NotificationRow)
                .filter_by(user_id=str(user_id))
                .order_by(NotificationRow.id.desc())
                .limit(limit)
                .all()
            )
            return [
                NotificationItem(str(r.id), r.kind, r.text, r.link, r.is_read, r.created_at.isoformat(),
                                 r.category or "", r.title or "", int((r.data or {}).get("count", 1)))
                for r in rows
            ]

    def unread_count(self, user_id) -> int:
        with self._sf() as s:
            return (
                s.query(func.count(NotificationRow.id))
                .filter_by(user_id=str(user_id), is_read=False)
                .scalar()
                or 0
            )

    def notification_version(self, user_id) -> tuple:
        with self._sf() as s:
            unread = s.query(func.count(NotificationRow.id)).filter_by(user_id=str(user_id), is_read=False).scalar() or 0
            maxid = s.query(func.max(NotificationRow.id)).filter_by(user_id=str(user_id)).scalar() or 0
            return (int(unread), int(maxid))

    def mark_read(self, user_id) -> None:
        with self._sf() as s:
            # reading an unread notification counts as "opened" for the funnel
            s.query(NotificationRow).filter_by(user_id=str(user_id), is_read=False).update(
                {"is_read": True, "opened_at": func.now()}
            )
            s.commit()

    def mark_clicked(self, user_id, notification_id) -> bool:
        try:
            nid = int(notification_id)
        except (TypeError, ValueError):
            return False
        with self._sf() as s:
            row = s.query(NotificationRow).filter_by(user_id=str(user_id), id=nid).first()
            if row is None:
                return False
            if row.clicked_at is None:
                row.clicked_at = func.now()
            if row.opened_at is None:
                row.opened_at = func.now()     # a click implies it was seen
            row.is_read = True
            s.commit()
            return True

    def delete_notification(self, user_id, notification_id) -> bool:
        try:
            nid = int(notification_id)
        except (TypeError, ValueError):
            return False
        with self._sf() as s:
            # scope to the recipient so a user can only delete their own
            n = s.query(NotificationRow).filter_by(user_id=str(user_id), id=nid).delete()
            s.commit()
            return bool(n)

    # ----- web-push subscriptions -----
    def add_subscription(self, user_id, endpoint, p256dh, auth, platform="web") -> None:
        with self._sf() as s:
            # endpoint is unique: re-subscribing updates keys + owner (upsert).
            row = s.query(PushSubscriptionRow).filter_by(endpoint=endpoint).first()
            if row is None:
                s.add(PushSubscriptionRow(
                    user_id=str(user_id), endpoint=endpoint,
                    p256dh=p256dh, auth=auth, platform=platform,
                ))
            else:
                row.user_id, row.p256dh, row.auth, row.platform = str(user_id), p256dh, auth, platform
            try:
                s.commit()
            except IntegrityError:
                s.rollback()

    def subscriptions_for_user(self, user_id) -> list[PushSubscription]:
        with self._sf() as s:
            rows = s.query(PushSubscriptionRow).filter_by(user_id=str(user_id)).all()
            return [PushSubscription(r.endpoint, r.p256dh, r.auth) for r in rows]

    def subscription_owner(self, endpoint) -> "str | None":
        with self._sf() as s:
            row = s.query(PushSubscriptionRow.user_id).filter_by(endpoint=endpoint).first()
            return row[0] if row else None

    def delete_subscription(self, endpoint, user_id=None) -> bool:
        with self._sf() as s:
            q = s.query(PushSubscriptionRow).filter_by(endpoint=endpoint)
            if user_id is not None:
                q = q.filter(PushSubscriptionRow.user_id == str(user_id))
            n = q.delete()
            s.commit()
            return bool(n)

    def delete_subscriptions_for_user(self, user_id) -> int:
        with self._sf() as s:
            n = s.query(PushSubscriptionRow).filter_by(user_id=str(user_id)).delete()
            s.commit()
            return int(n)

    # ----- admin announcements + engagement funnel -----
    def record_announcement(self, title, text, category, link, created_by, audience, recipients) -> str:
        with self._sf() as s:
            row = AnnouncementRow(
                title=title, text=text, category=category, link=link or "",
                created_by=str(created_by), audience=audience, recipients=int(recipients),
            )
            s.add(row)
            s.commit()
            return str(row.id)

    def list_announcements(self, limit=50) -> list[AnnouncementItem]:
        with self._sf() as s:
            rows = s.query(AnnouncementRow).order_by(AnnouncementRow.id.desc()).limit(limit).all()
            return [AnnouncementItem(str(r.id), r.title, r.text, r.category, r.link,
                                     r.created_by, r.audience, r.recipients, r.created_at.isoformat())
                    for r in rows]

    def campaign_counts(self) -> "dict[str, tuple[int, int, int]]":
        with self._sf() as s:
            rows = (
                s.query(
                    NotificationRow.campaign_id,
                    func.count(NotificationRow.id),
                    func.count(NotificationRow.opened_at),   # count() ignores NULLs → opened
                    func.count(NotificationRow.clicked_at),  # → clicked
                )
                .filter(NotificationRow.campaign_id.isnot(None))
                .group_by(NotificationRow.campaign_id)
                .all()
            )
            return {str(r[0]): (int(r[1]), int(r[2]), int(r[3])) for r in rows}
