"""Notification email channel — non-blocking sends over the shared Notifier.

The underlying SMTP send is blocking, so a broadcast to N users would serialise N
round-trips inside the request. Here each send is fire-and-forget on a small pool
(``_SYNC`` flips to inline for tests). The Notifier already swallows send errors, so
a failed email never surfaces to the caller.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor

from app.core.notifications import build_notifier

log = logging.getLogger("cricnetra.email")

_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="email")
_notifier = None
_SYNC = False  # tests set True to deliver inline


def _get_notifier():
    global _notifier
    if _notifier is None:
        _notifier = build_notifier()   # SMTP when configured, else a console logger
    return _notifier


def _send(to: str, subject: str, body: str) -> None:
    try:
        _get_notifier().send_email(to, subject, body)
    except Exception as exc:  # belt-and-suspenders (Notifier already swallows)
        log.warning("notification email to %s failed: %s", to, exc)


def send(to: str, subject: str, body: str) -> None:
    """Queue a notification email (non-blocking). No-op without a recipient address."""
    if not to:
        return
    if _SYNC:
        _send(to, subject, body)
    else:
        _pool.submit(_send, to, subject, body)
