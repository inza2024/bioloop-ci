"""Add pilot identity, session and mobile idempotency foundation.

Revision ID: 0004_pilot_auth
Revises:
Create Date: 2026-08-30
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_pilot_auth"
down_revision = None
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    return {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    tables = _tables()
    if "pilot_organizations" not in tables:
        op.create_table(
            "pilot_organizations",
            sa.Column("id", sa.String(40), primary_key=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("kind", sa.String(40), nullable=False),
            sa.Column("approval_status", sa.String(20), nullable=False),
            sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "pilot_users" not in tables:
        op.create_table(
            "pilot_users",
            sa.Column("id", sa.String(40), primary_key=True),
            sa.Column("display_name", sa.String(100), nullable=False),
            sa.Column("email_normalized", sa.String(254), nullable=False, unique=True),
            sa.Column("password_hash", sa.Text(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "pilot_memberships" not in tables:
        op.create_table(
            "pilot_memberships",
            sa.Column("id", sa.String(40), primary_key=True),
            sa.Column("user_id", sa.String(40), sa.ForeignKey("pilot_users.id"), nullable=False),
            sa.Column("organization_id", sa.String(40), sa.ForeignKey("pilot_organizations.id"), nullable=False),
            sa.Column("role", sa.String(40), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("approved_at", sa.DateTime(timezone=True)),
            sa.Column("approved_by_user_id", sa.String(40)),
            sa.UniqueConstraint("user_id", "organization_id", "role", name="uq_pilot_membership"),
        )
        op.create_index("idx_pilot_membership_user", "pilot_memberships", ["user_id", "status"])
    if "pilot_sessions" not in tables:
        op.create_table(
            "pilot_sessions",
            sa.Column("id", sa.String(40), primary_key=True),
            sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
            sa.Column("user_id", sa.String(40), sa.ForeignKey("pilot_users.id"), nullable=False),
            sa.Column("active_membership_id", sa.String(40), sa.ForeignKey("pilot_memberships.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True)),
        )
        op.create_index("idx_pilot_session_expiry", "pilot_sessions", ["expires_at", "revoked_at"])
    if "pilot_login_attempts" not in tables:
        op.create_table(
            "pilot_login_attempts",
            sa.Column("id", sa.String(40), primary_key=True),
            sa.Column("email_digest", sa.String(64), nullable=False),
            sa.Column("ip_digest", sa.String(64), nullable=False),
            sa.Column("success", sa.Boolean(), nullable=False),
            sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("idx_pilot_login_window", "pilot_login_attempts", ["email_digest", "ip_digest", "attempted_at"])
    if "pilot_role_invitations" not in tables:
        op.create_table(
            "pilot_role_invitations",
            sa.Column("id", sa.String(40), primary_key=True),
            sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
            sa.Column("email_digest", sa.String(64), nullable=False),
            sa.Column("organization_id", sa.String(40), sa.ForeignKey("pilot_organizations.id"), nullable=False),
            sa.Column("role", sa.String(40), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True)),
        )

    if "waste_declarations" in _tables() and "client_idempotency_key" not in _columns("waste_declarations"):
        with op.batch_alter_table("waste_declarations") as batch:
            batch.add_column(sa.Column("client_idempotency_key", sa.String(80), nullable=True))
            batch.create_index(
                "idx_declaration_owner_idempotency",
                ["owner_organization_id", "client_idempotency_key"],
                unique=True,
            )


def downgrade() -> None:
    # Pilot migrations are intentionally additive; local histories are never erased.
    pass
