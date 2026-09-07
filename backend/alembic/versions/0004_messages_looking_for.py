"""Add messages + looking_for tables (direct messages and the "Looking For" board).

Guarded with table-existence checks: the 0001 baseline runs create_all from the
*current* models, so on a fresh database these tables already exist (the create
would then fail). On an existing DB they're missing and get created here.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_messages_looking_for"
down_revision = "0003_player_user_claim"
branch_labels = None
depends_on = None


def _has_table(bind, table: str) -> bool:
    return sa.inspect(bind).has_table(table)


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind, "messages"):
        op.create_table(
            "messages",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("pair_key", sa.String(length=81), nullable=False),
            sa.Column("sender_id", sa.String(length=40), nullable=False),
            sa.Column("recipient_id", sa.String(length=40), nullable=False),
            sa.Column("text", sa.String(length=2000), nullable=False),
            sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_messages_pair_key", "messages", ["pair_key"])
        op.create_index("ix_messages_sender_id", "messages", ["sender_id"])
        op.create_index("ix_messages_recipient_id", "messages", ["recipient_id"])
        op.create_index("ix_messages_is_read", "messages", ["is_read"])
        op.create_index("ix_messages_created_at", "messages", ["created_at"])

    if not _has_table(bind, "looking_for"):
        op.create_table(
            "looking_for",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("author_id", sa.String(length=40), nullable=False),
            sa.Column("author_name", sa.String(length=100), nullable=False),
            sa.Column("kind", sa.String(length=20), nullable=False),
            sa.Column("text", sa.String(length=500), nullable=False),
            sa.Column("location", sa.String(length=120), nullable=True),
            sa.Column("role", sa.String(length=60), nullable=True),
            sa.Column("status", sa.String(length=12), nullable=False, server_default="open"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_looking_for_author_id", "looking_for", ["author_id"])
        op.create_index("ix_looking_for_kind", "looking_for", ["kind"])
        op.create_index("ix_looking_for_location", "looking_for", ["location"])
        op.create_index("ix_looking_for_status", "looking_for", ["status"])
        op.create_index("ix_looking_for_created_at", "looking_for", ["created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "looking_for"):
        op.drop_table("looking_for")
    if _has_table(bind, "messages"):
        op.drop_table("messages")
