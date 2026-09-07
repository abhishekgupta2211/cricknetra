"""Application settings (env-overridable via CRICNETRA_* vars or a .env file)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute path to backend/.env so it loads no matter the working directory
# (uvicorn from repo root, pytest, the preview runner, etc.).
_BASE_DIR = Path(__file__).resolve().parents[2]  # the backend/ directory
_ENV_FILE = _BASE_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CRICNETRA_", env_file=str(_ENV_FILE), extra="ignore"
    )

    app_name: str = "CricNetra API"
    version: str = "0.1.0"

    # SQLAlchemy URL. When set, the app persists to that database; when empty,
    # it falls back to an in-memory store (handy for quick demos / tests).
    # Put the real value in backend/.env (kept out of git). Example:
    #   CRICNETRA_DATABASE_URL=postgresql+psycopg://postgres:PASS@localhost:5432/CricNetra_db
    database_url: Optional[str] = None

    # Origins allowed to call the API from a browser. Defaults cover the common
    # React dev servers (Vite 5173, CRA 3000) so the future frontend just works.
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Auth / JWT. Override the secret in backend/.env for production
    # (CRICNETRA_SECRET_KEY=...). The default is for local dev only.
    secret_key: str = "dev-insecure-secret-change-me-in-production"
    algorithm: str = "HS256"
    # Short-lived access token + a long-lived, revocable refresh token (rotated on
    # every use). The client auto-refreshes; logout revokes the refresh token.
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # Per-IP rate limiting on the abuse-prone auth endpoints. Disabled in tests.
    rate_limit_enabled: bool = True

    # Account verification + password reset. With no SMS/email provider wired yet,
    # `auth_dev_delivery` returns the code/token in the API response (and logs it)
    # so the flow is testable end-to-end. Set False in production once a real
    # sender is connected, so secrets are never exposed over the API.
    auth_dev_delivery: bool = True
    verify_code_ttl_minutes: int = 15
    reset_token_ttl_minutes: int = 30

    # Observability. log_level is the root level; log_format is "console" (human
    # readable, good for dev) or "json" (one JSON object per line, good for log
    # aggregators in production — set CRICNETRA_LOG_FORMAT=json).
    log_level: str = "INFO"
    log_format: str = "console"

    # Notification delivery (OTP via SMS, password reset). Unset → a console
    # sender that only logs the message, so the flow is testable without a
    # provider. Set the Twilio vars to send real SMS / the SMTP vars for email.
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_from: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None
    smtp_starttls: bool = True

    # Auto-clipped video highlights. `ffmpeg_dir` overrides binary discovery (else
    # PATH / the winget install is used). `media_dir` holds uploaded recordings +
    # generated clips (needs a persistent volume in production).
    ffmpeg_dir: Optional[str] = None
    media_dir: str = str(_BASE_DIR / ".data")

    # Web Push (VAPID). If unset, a stable keypair is generated + persisted to
    # media_dir/vapid.json on first use. `vapid_subject` is the required contact.
    vapid_public_key: Optional[str] = None
    vapid_private_key: Optional[str] = None   # PEM
    vapid_subject: str = "mailto:admin@cricnetra.app"

    # Public base URL of the deployed app (e.g. https://cricnetra.app), used to turn
    # in-app hash links into absolute URLs in notification emails. Empty in dev.
    app_base_url: str = ""


settings = Settings()
