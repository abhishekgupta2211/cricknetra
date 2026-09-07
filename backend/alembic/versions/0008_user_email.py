"""Add users.email — optional, used for email OTP / password-reset delivery.

Guarded with a column-existence check because the 0001 baseline runs create_all
from the *current* models, which already includes this column on a fresh
database (so the add would then fail). On an existing DB the column is missing
and gets added here.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_user_email"
down_revision = "0007_venues"
branch_labels = None
depends_on = None


def _has_column(bind, table: str, column: str) -> bool:
    insp = sa.inspect(bind)
    if not insp.has_table(table):
        return False
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    if _has_column(bind, "users", "email"):
        return
    op.add_column("users", sa.Column("email", sa.String(length=255), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if _has_column(bind, "users", "email"):
        op.drop_column("users", "email")
