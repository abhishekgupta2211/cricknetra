"""auth_tokens — mobile verification codes + password-reset tokens

The baseline (0001) creates the schema from live metadata, which on a *fresh*
database already includes this table; so we guard with an existence check and
only create it where it's missing (e.g. the existing production DB).

Revision ID: 0002_auth_tokens
Revises: 0001_baseline
Create Date: 2026-06-17
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_auth_tokens"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("auth_tokens"):
        return  # already created by the baseline's create_all on a fresh DB
    op.create_table(
        "auth_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(length=40), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_auth_tokens_user_id", "auth_tokens", ["user_id"])
    op.create_index("ix_auth_tokens_kind", "auth_tokens", ["kind"])
    op.create_index("ix_auth_tokens_token_hash", "auth_tokens", ["token_hash"])


def downgrade() -> None:
    op.drop_table("auth_tokens")
