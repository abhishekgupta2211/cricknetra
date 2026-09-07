"""Safe live-stream embedding — Option A "bring your own stream".

An organiser attaches a link to their OWN YouTube / Facebook live stream to a
match; no video ever touches our servers. We never drop an arbitrary URL into an
``<iframe src>`` — only links we can map to a known provider's official embed
endpoint get an ``embed_url``. Anything else valid is kept as an ``external`` link
(rendered as a "Watch live" button, never an iframe).
"""

from __future__ import annotations

import re
from typing import Optional
from urllib.parse import parse_qs, quote, urlparse

from pydantic import BaseModel

_YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_YT_PATH = re.compile(r"^/(?:live|embed|shorts|v)/([A-Za-z0-9_-]{11})")


class StreamInfo(BaseModel):
    """How the client should render a match's live stream."""

    url: str                          # the raw link the organiser pasted
    kind: str                         # "youtube" | "facebook" | "external"
    embed_url: Optional[str] = None   # safe <iframe> src, or None → watch-link only


def _dehost(hostname: Optional[str]) -> str:
    host = (hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _youtube_id(u) -> Optional[str]:
    """Extract an 11-char video id from any YouTube watch / youtu.be / live URL."""
    host = _dehost(u.hostname)
    if host == "youtu.be":
        vid = u.path.lstrip("/").split("/", 1)[0]
        return vid if _YT_ID.match(vid) else None
    if host in ("youtube.com", "m.youtube.com", "music.youtube.com"):
        if u.path == "/watch":
            vid = parse_qs(u.query).get("v", [""])[0]
            return vid if _YT_ID.match(vid) else None
        m = _YT_PATH.match(u.path)
        if m:
            return m.group(1)
    return None


def stream_info(raw: Optional[str]) -> Optional[StreamInfo]:
    """Validate + classify a pasted stream URL. Returns ``None`` when it's blank
    or not a usable http(s) link — the caller treats that as "clear the stream"."""
    if not raw:
        return None
    raw = raw.strip()
    if not raw or len(raw) > 500:
        return None
    u = urlparse(raw)
    if u.scheme not in ("http", "https") or not u.hostname:
        return None

    vid = _youtube_id(u)
    if vid:
        return StreamInfo(url=raw, kind="youtube", embed_url=f"https://www.youtube.com/embed/{vid}")

    if _dehost(u.hostname) in ("facebook.com", "m.facebook.com", "fb.watch", "fb.gg"):
        embed = "https://www.facebook.com/plugins/video.php?show_text=false&href=" + quote(raw, safe="")
        return StreamInfo(url=raw, kind="facebook", embed_url=embed)

    # A valid link we can't safely iframe → keep it as an external "Watch live" link.
    return StreamInfo(url=raw, kind="external", embed_url=None)
