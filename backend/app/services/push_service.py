"""Web Push delivery — fan a notification out to a user's registered devices.

Sends run on a small background thread pool so scoring / request handlers never
block on push HTTP. Dead subscriptions (404 / 410 Gone) are pruned automatically.
A safe no-op when pywebpush isn't installed. Tests flip ``_SYNC`` to deliver inline.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from app.core import webpush

log = logging.getLogger("cricnetra.push")

# Small pool: pushes are I/O-bound and fire-and-forget. Daemon threads so a send
# in flight never holds up shutdown.
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="push")

# Tests set this True so delivery is synchronous (and assertable) instead of queued.
_SYNC = False


def _push_url(link: str) -> str:
    """Map an in-app hash link (``#/match/12``) to a URL the SW can open."""
    if not link:
        return "/app/"
    if link.startswith("#"):
        return "/app/" + link
    return link


def _deliver(social, user_id: str, payload: dict) -> None:
    """Push ``payload`` to every device of ``user_id``; prune ones that are gone."""
    for sub in social.subscriptions_for_user(user_id):
        try:
            code = webpush.send(sub.to_info(), payload)
            if code in (404, 410):
                social.delete_subscription(sub.endpoint, user_id)
        except Exception as exc:  # WebPushException (or transport error)
            resp = getattr(exc, "response", None)
            code = getattr(resp, "status_code", None)
            if code in (404, 410):
                social.delete_subscription(sub.endpoint, user_id)
            else:
                log.warning("push to user %s failed: %s", user_id, exc)


def send_to_user(social, user_id: str, *, title: str, body: str, link: str = "",
                 tag: "str | None" = None, category: "str | None" = None) -> None:
    """Queue a push to all of a user's devices (non-blocking). No-op if unavailable."""
    if not webpush.available():
        return
    payload = {
        "title": title, "body": body, "url": _push_url(link),
        "tag": tag or category or "cricnetra", "category": category,
    }
    if _SYNC:
        _deliver(social, str(user_id), payload)
    else:
        _pool.submit(_deliver, social, str(user_id), payload)
