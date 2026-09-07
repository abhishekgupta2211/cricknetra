"""Add tournaments.config + fixtures.group (group stage + playoffs + points config).

Guarded with column-existence checks because the 0001 baseline runs create_all
from the current models, which already include these columns on a fresh DB.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0005_tournament_groups"
down_revision = "0004_messages_looking_for"
branch_labels = None
depends_on = None

# JSONB on Postgres, generic JSON elsewhere — mirrors app.db.models.JSONType.
_JSON = sa.JSON().with_variant(JSONB, "postgresql")


def _has_column(bind, table: str, column: str) -> bool:
    insp = sa.inspect(bind)
    if not insp.has_table(table):
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_column(bind, "tournaments", "config"):
        op.add_column("tournaments", sa.Column("config", _JSON, nullable=True))
    if not _has_column(bind, "fixtures", "group"):
        op.add_column("fixtures", sa.Column("group", sa.String(length=8), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if _has_column(bind, "fixtures", "group"):
        op.drop_column("fixtures", "group")
    if _has_column(bind, "tournaments", "config"):
        op.drop_column("tournaments", "config")
