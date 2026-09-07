"""Add matches.stream_url — optional bring-your-own live-stream link.

Guarded with a column-existence check (mirrors 0008): the 0001 baseline runs
create_all from the current models, which already includes this column on a
fresh database, so the add would fail there. On an existing DB the column is
missing and gets added here.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_match_stream_url"
down_revision = "0008_user_email"
branch_labels = None
depends_on = None


def _has_column(bind, table: str, column: str) -> bool:
    insp = sa.inspect(bind)
    if not insp.has_table(table):
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    if _has_column(bind, "matches", "stream_url"):
        return
    op.add_column("matches", sa.Column("stream_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if _has_column(bind, "matches", "stream_url"):
        op.drop_column("matches", "stream_url")
