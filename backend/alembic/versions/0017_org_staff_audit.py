"""Areas, organizations, organizer profiles, tournament staff and the audit trail.

These five registries had no SQL implementation, so on a Postgres deployment
they lived in whichever worker wrote them and were lost on restart. The tables
land here so the repositories in ``sql_org_repository`` / ``sql_tournament_staff_repository``
/ ``sql_audit_repository`` have something to write to.

Guarded (mirrors 0012-0016): the 0001 baseline runs create_all from the current
models, so a fresh database already has these; here we only create what is
missing on an existing one.

Revision ID: 0017_org_staff_audit
Revises: 0016_announcements
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0017_org_staff_audit"
down_revision = "0016_announcements"
branch_labels = None
depends_on = None


def _has_table(bind, table: str) -> bool:
    return sa.inspect(bind).has_table(table)


def _index(bind, table: str, name: str, columns: list[str]) -> None:
    """Create an index unless the table already carries one by that name —
    create_all made these on a fresh database, so this migration has to be a
    no-op there rather than an error."""
    existing = {ix["name"] for ix in sa.inspect(bind).get_indexes(table)}
    if name not in existing:
        op.create_index(name, table, columns)


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind, "areas"):
        op.create_table(
            "areas",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("state", sa.String(80), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        _index(bind, "areas", "ix_areas_name", ["name"])

    if not _has_table(bind, "organizations"):
        op.create_table(
            "organizations",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(140), nullable=False),
            sa.Column("area_id", sa.String(40), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        _index(bind, "organizations", "ix_organizations_name", ["name"])
        _index(bind, "organizations", "ix_organizations_area_id", ["area_id"])

    if not _has_table(bind, "organizer_profiles"):
        op.create_table(
            "organizer_profiles",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.String(40), nullable=False),
            sa.Column("area_id", sa.String(40), nullable=True),
            sa.Column("organization_id", sa.String(40), nullable=True),
            sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
            sa.Column("created_by", sa.String(40), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            # One profile per account: upsert_organizer moves the existing row
            # rather than adding a second, and two rows would make "is this
            # organizer suspended?" answerable two ways.
            sa.UniqueConstraint("user_id", name="uq_organizer_profile_user"),
        )
        _index(bind, "organizer_profiles", "ix_organizer_profiles_user_id", ["user_id"])
        _index(bind, "organizer_profiles", "ix_organizer_profiles_area_id", ["area_id"])

    if not _has_table(bind, "tournament_staff"):
        op.create_table(
            "tournament_staff",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("tournament_id", sa.String(40), nullable=False),
            sa.Column("user_id", sa.String(40), nullable=False),
            sa.Column("staff_role", sa.String(20), nullable=False),
            sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
            sa.Column("added_by", sa.String(40), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            # Re-adding somebody who was removed reinstates their entry instead
            # of creating a second one that set_active would leave behind.
            sa.UniqueConstraint(
                "tournament_id", "user_id", "staff_role", name="uq_tournament_staff"
            ),
        )
        _index(bind, "tournament_staff", "ix_tournament_staff_tournament_id", ["tournament_id"])
        _index(bind, "tournament_staff", "ix_tournament_staff_user_id", ["user_id"])
        _index(bind, "tournament_staff", "ix_tournament_staff_staff_role", ["staff_role"])

    if not _has_table(bind, "audit_log"):
        op.create_table(
            "audit_log",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("actor_id", sa.String(40), nullable=True),
            sa.Column("action", sa.String(40), nullable=False),
            sa.Column("resource_type", sa.String(30), nullable=False, server_default=""),
            sa.Column("resource_id", sa.String(40), nullable=False, server_default=""),
            sa.Column("detail", sa.String(500), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        _index(bind, "audit_log", "ix_audit_log_actor_id", ["actor_id"])
        _index(bind, "audit_log", "ix_audit_log_action", ["action"])
        _index(bind, "audit_log", "ix_audit_log_resource_type", ["resource_type"])
        _index(bind, "audit_log", "ix_audit_log_resource_id", ["resource_id"])
        _index(bind, "audit_log", "ix_audit_log_created_at", ["created_at"])


def downgrade() -> None:
    """Drop them again — children before parents, though the references between
    these tables are plain string ids with no foreign keys, exactly as
    resource_owners and match_officials already do."""
    bind = op.get_bind()
    for table in (
        "audit_log",
        "tournament_staff",
        "organizer_profiles",
        "organizations",
        "areas",
    ):
        if _has_table(bind, table):
            op.drop_table(table)
