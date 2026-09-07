"""Add matches.clips — optional list of bring-your-own highlight clip links.

Guarded with a column-existence check (mirrors 0008/0009): the 0001 baseline runs
create_all from the current models, which already includes this column on a fresh
database, so the add would fail there. On an existing DB it's missing and added here.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

revision = "0010_match_clips"
down_revision = "0009_match_stream_url"
branch_labels = None
depends_on = None

_JSON = JSON().with_variant(JSONB, "postgresql")


def _has_column(bind, table: str, column: str) -> bool:
    insp = sa.inspect(bind)
    if not insp.has_table(table):
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    if _has_column(bind, "matches", "clips"):
        return
    op.add_column("matches", sa.Column("clips", _JSON, nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if _has_column(bind, "matches", "clips"):
        op.drop_column("matches", "clips")
