"""Smart delivery (P3) — coalescing key on notifications + sound / tz_offset prefs.

Guarded (mirrors 0012/0013): the 0001 baseline runs create_all from current models,
so these already exist on a fresh DB; here we only add what's missing on an existing one.
All new columns are nullable / defaulted, so old rows are unaffected.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0014_smart_delivery"
down_revision = "0013_push_subscriptions"
branch_labels = None
depends_on = None


def _has_column(bind, table: str, column: str) -> bool:
    insp = sa.inspect(bind)
    return insp.has_table(table) and any(c["name"] == column for c in insp.get_columns(table))


def _has_index(bind, table: str, name: str) -> bool:
    insp = sa.inspect(bind)
    return insp.has_table(table) and any(ix["name"] == name for ix in insp.get_indexes(table))


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_column(bind, "notifications", "group_key"):
        op.add_column("notifications", sa.Column("group_key", sa.String(60), nullable=True))
    if not _has_index(bind, "notifications", "ix_notifications_group_key"):
        op.create_index("ix_notifications_group_key", "notifications", ["group_key"])

    if not _has_column(bind, "notification_prefs", "sound"):
        op.add_column("notification_prefs",
                      sa.Column("sound", sa.Boolean, nullable=False, server_default=sa.true()))
    if not _has_column(bind, "notification_prefs", "tz_offset"):
        op.add_column("notification_prefs",
                      sa.Column("tz_offset", sa.Integer, nullable=False, server_default="0"))


def downgrade() -> None:
    bind = op.get_bind()
    for col in ["sound", "tz_offset"]:
        if _has_column(bind, "notification_prefs", col):
            op.drop_column("notification_prefs", col)
    if _has_index(bind, "notifications", "ix_notifications_group_key"):
        op.drop_index("ix_notifications_group_key", "notifications")
    if _has_column(bind, "notifications", "group_key"):
        op.drop_column("notifications", "group_key")
