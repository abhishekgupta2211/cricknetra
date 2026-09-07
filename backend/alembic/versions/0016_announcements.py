"""Admin announcements + notification engagement funnel (P5).

Guarded (mirrors 0012-0015): the 0001 baseline runs create_all from current models,
so these already exist on a fresh DB; here we only add what's missing on an existing one.
Adding nullable columns to notifications is invisible to old rows.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0016_announcements"
down_revision = "0015_awards"
branch_labels = None
depends_on = None


def _has_table(bind, table: str) -> bool:
    return sa.inspect(bind).has_table(table)


def _has_column(bind, table: str, column: str) -> bool:
    insp = sa.inspect(bind)
    return insp.has_table(table) and any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()

    for col, type_ in [
        ("campaign_id", sa.String(40)),
        ("opened_at", sa.DateTime(timezone=True)),
        ("clicked_at", sa.DateTime(timezone=True)),
    ]:
        if not _has_column(bind, "notifications", col):
            op.add_column("notifications", sa.Column(col, type_, nullable=True))
    # index campaign_id for the per-campaign aggregation (safe if it already exists)
    insp = sa.inspect(bind)
    if _has_column(bind, "notifications", "campaign_id"):
        existing = {ix["name"] for ix in insp.get_indexes("notifications")}
        if "ix_notifications_campaign_id" not in existing:
            op.create_index("ix_notifications_campaign_id", "notifications", ["campaign_id"])

    if not _has_table(bind, "announcements"):
        op.create_table(
            "announcements",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("title", sa.String(120)),
            sa.Column("text", sa.String(255)),
            sa.Column("category", sa.String(20), server_default="system"),
            sa.Column("link", sa.String(160), server_default=""),
            sa.Column("created_by", sa.String(40)),
            sa.Column("audience", sa.String(20), server_default="all"),
            sa.Column("recipients", sa.Integer, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "announcements"):
        op.drop_table("announcements")
    insp = sa.inspect(bind)
    if _has_table(bind, "notifications"):
        existing = {ix["name"] for ix in insp.get_indexes("notifications")}
        if "ix_notifications_campaign_id" in existing:
            op.drop_index("ix_notifications_campaign_id", "notifications")
    for col in ["campaign_id", "opened_at", "clicked_at"]:
        if _has_column(bind, "notifications", col):
            op.drop_column("notifications", col)
