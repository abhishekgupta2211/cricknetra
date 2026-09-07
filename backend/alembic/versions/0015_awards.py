"""Awards (P4) — persisted match awards (MoM / best batter / best bowler).

Guarded (mirrors 0012-0014): the 0001 baseline runs create_all from current models,
so this already exists on a fresh DB; here we only create it if missing on an existing one.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0015_awards"
down_revision = "0014_smart_delivery"
branch_labels = None
depends_on = None


def _has_table(bind, table: str) -> bool:
    return sa.inspect(bind).has_table(table)


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, "awards"):
        op.create_table(
            "awards",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("match_id", sa.String(40), index=True),
            sa.Column("award_type", sa.String(20)),
            sa.Column("player_key", sa.String(60), index=True),
            sa.Column("player_name", sa.String(100)),
            sa.Column("detail", sa.String(80), server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("match_id", "award_type", name="uq_award_match_type"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "awards"):
        op.drop_table("awards")
