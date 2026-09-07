"""Web Push (VAPID) — a stable server keypair + a send() over pywebpush.

The keypair is loaded from settings, else a persisted file (media_dir/vapid.json),
else generated once and persisted — so browser subscriptions survive restarts. Kept
behind a tiny seam (send/available/application_server_key) so a native FCM sender can
be added later without touching callers.
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Optional

from app.core.config import settings

log = logging.getLogger("cricnetra.webpush")


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


_cache: Optional[dict] = None


def _keys() -> dict:
    """Load/derive {'app_server_key', 'private_pem'} once (cached)."""
    global _cache
    if _cache is not None:
        return _cache
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    priv_pem = settings.vapid_private_key
    if not priv_pem:
        path = Path(settings.media_dir) / "vapid.json"
        if path.exists():
            try:
                priv_pem = json.loads(path.read_text()).get("private_pem")
            except Exception:
                priv_pem = None
        if not priv_pem:
            key = ec.generate_private_key(ec.SECP256R1())
            priv_pem = key.private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            ).decode("ascii")
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({"private_pem": priv_pem}))
            except Exception:
                log.warning("could not persist VAPID key — it will change on restart")

    pk = serialization.load_pem_private_key(priv_pem.encode("ascii"), password=None)
    raw_pub = pk.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint,
    )
    _cache = {"app_server_key": _b64url(raw_pub), "private_pem": priv_pem}
    return _cache


def application_server_key() -> str:
    """The base64url raw public key the browser passes to pushManager.subscribe()."""
    return settings.vapid_public_key or _keys()["app_server_key"]


def available() -> bool:
    try:
        import pywebpush  # noqa: F401
        return True
    except Exception:
        return False


def send(subscription: dict, payload: dict, ttl: int = 3600) -> int:
    """Deliver one push; returns the endpoint status code. Raises on transport error.
    A 404/410 means the subscription is gone — the caller should prune it."""
    from pywebpush import webpush
    resp = webpush(
        subscription_info=subscription,
        data=json.dumps(payload),
        vapid_private_key=_keys()["private_pem"],
        vapid_claims={"sub": settings.vapid_subject},
        ttl=ttl,
    )
    return getattr(resp, "status_code", 201)
