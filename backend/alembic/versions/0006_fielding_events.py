"""Add fielding_events table (dropped catches / runs saved / misfields).

Guarded with a table-existence check: the 0001 baseline runs create_all from the
current models, so on a fresh DB this table already exists.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_fielding_events"
down_revision = "0005_tournament_groups"
branch_labels = None
depends_on = None


def _has_table(bind, table: str) -> bool:
    return sa.inspect(bind).has_table(table)


def upgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "fielding_events"):
        return
    op.create_table(
        "fielding_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("match_id", sa.String(length=40), nullable=False),
        sa.Column("innings", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("fielder", sa.String(length=120), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("runs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bowler", sa.String(length=120), nullable=True),
        sa.Column("batter", sa.String(length=120), nullable=True),
        sa.Column("note", sa.String(length=200), nullable=True),
        sa.Column("over_ball", sa.String(length=12), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_fielding_events_match_id", "fielding_events", ["match_id"])
    op.create_index("ix_fielding_events_kind", "fielding_events", ["kind"])
    op.create_index("ix_fielding_events_created_at", "fielding_events", ["created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "fielding_events"):
        op.drop_table("fielding_events")
