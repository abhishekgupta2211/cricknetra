"""Web Push — push_subscriptions table (one row per browser/device endpoint).

Guarded (mirrors 0012): the 0001 baseline runs create_all from current models, so
this already exists on a fresh DB; here we only create it if missing on an existing one.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0013_push_subscriptions"
down_revision = "0012_notifications_v2"
branch_labels = None
depends_on = None


def _has_table(bind, table: str) -> bool:
    return sa.inspect(bind).has_table(table)


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, "push_subscriptions"):
        op.create_table(
            "push_subscriptions",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.String(40), index=True),
            sa.Column("endpoint", sa.String(500)),
            sa.Column("p256dh", sa.String(120)),
            sa.Column("auth", sa.String(60)),
            sa.Column("platform", sa.String(20), server_default="web"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("last_seen", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("endpoint", name="uq_push_endpoint"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "push_subscriptions"):
        op.drop_table("push_subscriptions")
