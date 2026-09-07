"""Notifications v2 — entity_follows + notification_prefs tables, and richer
notifications (category / title / entity / data).

Guarded (mirrors 0007/0011): the 0001 baseline runs create_all from current models,
so these already exist on a fresh DB; here we only add what's missing on an existing
one. Enriching notifications with nullable columns is invisible to old rows.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

revision = "0012_notifications_v2"
down_revision = "0011_match_meta"
branch_labels = None
depends_on = None

_JSON = JSON().with_variant(JSONB, "postgresql")


def _has_table(bind, table: str) -> bool:
    return sa.inspect(bind).has_table(table)


def _has_column(bind, table: str, column: str) -> bool:
    insp = sa.inspect(bind)
    return insp.has_table(table) and any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()

    for col, type_ in [
        ("category", sa.String(20)), ("title", sa.String(120)),
        ("entity_type", sa.String(20)), ("entity_id", sa.String(40)), ("data", _JSON),
    ]:
        if not _has_column(bind, "notifications", col):
            op.add_column("notifications", sa.Column(col, type_, nullable=True))

    if not _has_table(bind, "entity_follows"):
        op.create_table(
            "entity_follows",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("follower_id", sa.String(40), index=True),
            sa.Column("entity_type", sa.String(20)),
            sa.Column("entity_id", sa.String(40)),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("follower_id", "entity_type", "entity_id", name="uq_entity_follow"),
        )
        op.create_index("ix_entity_follow_target", "entity_follows", ["entity_type", "entity_id"])

    if not _has_table(bind, "notification_prefs"):
        T, F = sa.true(), sa.false()
        op.create_table(
            "notification_prefs",
            sa.Column("user_id", sa.String(40), primary_key=True),
            sa.Column("match", sa.Boolean, server_default=T),
            sa.Column("tournament", sa.Boolean, server_default=T),
            sa.Column("team", sa.Boolean, server_default=T),
            sa.Column("player", sa.Boolean, server_default=T),
            sa.Column("social", sa.Boolean, server_default=T),
            sa.Column("system", sa.Boolean, server_default=T),
            sa.Column("achievement", sa.Boolean, server_default=T),
            sa.Column("marketing", sa.Boolean, server_default=F),
            sa.Column("email_enabled", sa.Boolean, server_default=F),
            sa.Column("push_enabled", sa.Boolean, server_default=T),
            sa.Column("quiet_start", sa.Integer, nullable=True),
            sa.Column("quiet_end", sa.Integer, nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "notification_prefs"):
        op.drop_table("notification_prefs")
    if _has_table(bind, "entity_follows"):
        op.drop_table("entity_follows")
    for col in ["category", "title", "entity_type", "entity_id", "data"]:
        if _has_column(bind, "notifications", col):
            op.drop_column("notifications", col)
