"""Add venues table (grounds + coaching academies directory).

Guarded with a table-existence check: the 0001 baseline runs create_all from the
current models, so on a fresh DB this table already exists.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_venues"
down_revision = "0006_fielding_events"
branch_labels = None
depends_on = None


def _has_table(bind, table: str) -> bool:
    return sa.inspect(bind).has_table(table)


def upgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "venues"):
        return
    op.create_table(
        "venues",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("contact", sa.String(length=60), nullable=True),
        sa.Column("note", sa.String(length=300), nullable=True),
        sa.Column("created_by", sa.String(length=40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_venues_name", "venues", ["name"])
    op.create_index("ix_venues_kind", "venues", ["kind"])
    op.create_index("ix_venues_city", "venues", ["city"])
    op.create_index("ix_venues_created_by", "venues", ["created_by"])
    op.create_index("ix_venues_created_at", "venues", ["created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "venues"):
        op.drop_table("venues")
