"""Add players.user_id — roster player ↔ user account claim link.

Guarded with a column-existence check because the 0001 baseline runs
create_all from the *current* models, which already includes this column on a
fresh database (so the add would then fail). On an existing DB the column is
missing and gets added here.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_player_user_claim"
down_revision = "0002_auth_tokens"
branch_labels = None
depends_on = None


def _has_column(bind, table: str, column: str) -> bool:
    insp = sa.inspect(bind)
    if not insp.has_table(table):
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    if _has_column(bind, "players", "user_id"):
        return
    op.add_column("players", sa.Column("user_id", sa.String(length=40), nullable=True))
    op.create_index("ix_players_user_id", "players", ["user_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if _has_column(bind, "players", "user_id"):
        op.drop_index("ix_players_user_id", table_name="players")
        op.drop_column("players", "user_id")
