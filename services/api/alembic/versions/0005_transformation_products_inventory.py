"""Add administration, transformation, qualified products and inventory.

Revision ID: 0005_transformation_inventory
Revises: 0004_pilot_auth
Create Date: 2026-09-02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0005_transformation_inventory"
down_revision = "0004_pilot_auth"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    return {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    tables = _tables()
    if "pilot_organizations" in tables and "site_id" not in _columns("pilot_organizations"):
        with op.batch_alter_table("pilot_organizations") as batch:
            batch.add_column(sa.Column("site_id", sa.String(40)))

    if "pilot_role_invitations" in tables:
        invitation_columns = _columns("pilot_role_invitations")
        with op.batch_alter_table("pilot_role_invitations") as batch:
            if "created_at" not in invitation_columns:
                batch.add_column(sa.Column("created_at", sa.DateTime(timezone=True)))
            if "invited_by_user_id" not in invitation_columns:
                batch.add_column(sa.Column("invited_by_user_id", sa.String(40)))
            if "used_by_user_id" not in invitation_columns:
                batch.add_column(sa.Column("used_by_user_id", sa.String(40)))
            if "revoked_at" not in invitation_columns:
                batch.add_column(sa.Column("revoked_at", sa.DateTime(timezone=True)))

    tables = _tables()
    if "pilot_admin_actions" not in tables:
        op.create_table(
            "pilot_admin_actions",
            sa.Column("id", sa.String(40), primary_key=True),
            sa.Column("action", sa.String(50), nullable=False),
            sa.Column("subject_type", sa.String(40), nullable=False),
            sa.Column("subject_id", sa.String(80), nullable=False),
            sa.Column("decision", sa.String(30)),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("actor_user_id", sa.String(40), nullable=False),
            sa.Column("actor_organization_id", sa.String(40), nullable=False),
            sa.Column("actor_role", sa.String(40), nullable=False),
            sa.Column("correlation_id", sa.String(100), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "idx_pilot_admin_actions_subject",
            "pilot_admin_actions",
            ["subject_type", "subject_id", "created_at"],
        )

    if "transformation_runs" not in tables:
        op.create_table(
            "transformation_runs",
            sa.Column("id", sa.String(40), primary_key=True),
            sa.Column("operator_organization_id", sa.String(40), nullable=False),
            sa.Column("processing_unit_id", sa.String(40), nullable=False),
            sa.Column("process", sa.String(120), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True)),
            sa.Column("completed_at", sa.DateTime(timezone=True)),
            sa.Column("operator_user_id", sa.String(40), nullable=False),
            sa.Column("loss_quantity", sa.String(40)),
            sa.Column("loss_unit", sa.String(20)),
            sa.Column("loss_method", sa.String(120)),
            sa.Column("loss_measured_at", sa.DateTime(timezone=True)),
            sa.Column("loss_proof_level", sa.String(2)),
            sa.Column("correlation_id", sa.String(100), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "status IN ('planned', 'in_progress', 'completed', 'cancelled')",
                name="ck_transformation_status",
            ),
        )
        op.create_index(
            "idx_transformation_operator",
            "transformation_runs",
            ["operator_organization_id", "created_at"],
        )

    if "transformation_inputs" not in tables:
        op.create_table(
            "transformation_inputs",
            sa.Column("transformation_id", sa.String(40), sa.ForeignKey("transformation_runs.id"), nullable=False),
            sa.Column("lot_id", sa.String(40), sa.ForeignKey("lots.id"), nullable=False),
            sa.Column("measured_quantity", sa.String(40), nullable=False),
            sa.Column("quantity_unit", sa.String(20), nullable=False),
            sa.Column("measurement_method", sa.String(120), nullable=False),
            sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("provenance", sa.String(20), nullable=False),
            sa.Column("proof_level", sa.String(2), nullable=False),
            sa.PrimaryKeyConstraint("transformation_id", "lot_id"),
            sa.UniqueConstraint("lot_id", name="uq_transformation_input_lot"),
        )

    if "transformation_evidence" not in tables:
        op.create_table(
            "transformation_evidence",
            sa.Column("transformation_id", sa.String(40), sa.ForeignKey("transformation_runs.id"), nullable=False),
            sa.Column("evidence_id", sa.String(40), sa.ForeignKey("evidence.id"), nullable=False),
            sa.PrimaryKeyConstraint("transformation_id", "evidence_id"),
        )

    if "product_batches" not in tables:
        op.create_table(
            "product_batches",
            sa.Column("id", sa.String(40), primary_key=True),
            sa.Column("transformation_id", sa.String(40), sa.ForeignKey("transformation_runs.id"), nullable=False),
            sa.Column("owner_organization_id", sa.String(40), nullable=False),
            sa.Column("category", sa.String(50), nullable=False),
            sa.Column("quantity", sa.String(40), nullable=False),
            sa.Column("unit", sa.String(20), nullable=False),
            sa.Column("measurement_method", sa.String(120), nullable=False),
            sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("evidence_id", sa.String(40)),
            sa.Column("provenance", sa.String(20), nullable=False),
            sa.Column("proof_level", sa.String(2), nullable=False),
            sa.Column("quality_status", sa.String(30), nullable=False),
            sa.Column("location", sa.String(120), nullable=False),
            sa.Column("correlation_id", sa.String(100), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "quality_status IN ('quarantine', 'pending_analysis', 'released', 'rejected')",
                name="ck_product_quality_status",
            ),
        )
        op.create_index(
            "idx_product_visibility",
            "product_batches",
            ["quality_status", "category", "location"],
        )

    if "product_quality_tests" not in tables:
        op.create_table(
            "product_quality_tests",
            sa.Column("id", sa.String(40), primary_key=True),
            sa.Column("product_batch_id", sa.String(40), sa.ForeignKey("product_batches.id"), nullable=False),
            sa.Column("parameter", sa.String(100), nullable=False),
            sa.Column("value", sa.String(80), nullable=False),
            sa.Column("unit", sa.String(40), nullable=False),
            sa.Column("method", sa.String(160), nullable=False),
            sa.Column("laboratory_or_actor", sa.String(160), nullable=False),
            sa.Column("document_reference", sa.String(180)),
            sa.Column("tested_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("actor_user_id", sa.String(40), nullable=False),
            sa.Column("actor_organization_id", sa.String(40), nullable=False),
            sa.Column("provenance", sa.String(20), nullable=False),
            sa.Column("proof_level", sa.String(2), nullable=False),
            sa.Column("correlation_id", sa.String(100), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "idx_quality_test_product",
            "product_quality_tests",
            ["product_batch_id", "tested_at"],
        )

    if "product_release_events" not in tables:
        op.create_table(
            "product_release_events",
            sa.Column("id", sa.String(40), primary_key=True),
            sa.Column("product_batch_id", sa.String(40), sa.ForeignKey("product_batches.id"), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("note", sa.Text(), nullable=False),
            sa.Column("actor_user_id", sa.String(40), nullable=False),
            sa.Column("actor_organization_id", sa.String(40), nullable=False),
            sa.Column("proof_level", sa.String(2), nullable=False),
            sa.Column("correlation_id", sa.String(100), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("status IN ('released', 'rejected')", name="ck_product_release_status"),
        )

    if "customer_reservations" not in tables:
        op.create_table(
            "customer_reservations",
            sa.Column("id", sa.String(40), primary_key=True),
            sa.Column("product_batch_id", sa.String(40), sa.ForeignKey("product_batches.id"), nullable=False),
            sa.Column("customer_organization_id", sa.String(40), nullable=False),
            sa.Column("quantity", sa.String(40), nullable=False),
            sa.Column("unit", sa.String(20), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("idempotency_key", sa.String(100), nullable=False),
            sa.Column("actor_user_id", sa.String(40), nullable=False),
            sa.Column("correlation_id", sa.String(100), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("cancelled_at", sa.DateTime(timezone=True)),
            sa.Column("delivered_at", sa.DateTime(timezone=True)),
            sa.UniqueConstraint(
                "customer_organization_id",
                "idempotency_key",
                name="uq_customer_reservation_idempotency",
            ),
            sa.CheckConstraint(
                "status IN ('active', 'cancelled', 'delivered')",
                name="ck_customer_reservation_status",
            ),
        )

    if "inventory_movements" not in tables:
        op.create_table(
            "inventory_movements",
            sa.Column("id", sa.String(40), primary_key=True),
            sa.Column("product_batch_id", sa.String(40), sa.ForeignKey("product_batches.id"), nullable=False),
            sa.Column("movement_type", sa.String(30), nullable=False),
            sa.Column("quantity", sa.String(40), nullable=False),
            sa.Column("unit", sa.String(20), nullable=False),
            sa.Column("on_hand_delta", sa.String(40), nullable=False),
            sa.Column("reserved_delta", sa.String(40), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("reservation_id", sa.String(40), sa.ForeignKey("customer_reservations.id")),
            sa.Column("idempotency_key", sa.String(120), unique=True),
            sa.Column("actor_user_id", sa.String(40), nullable=False),
            sa.Column("actor_organization_id", sa.String(40), nullable=False),
            sa.Column("provenance", sa.String(20), nullable=False),
            sa.Column("proof_level", sa.String(2), nullable=False),
            sa.Column("correlation_id", sa.String(100), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "movement_type IN ('production', 'adjustment', 'reservation', 'cancellation', 'delivery')",
                name="ck_inventory_movement_type",
            ),
        )
        op.create_index(
            "idx_inventory_movement_product",
            "inventory_movements",
            ["product_batch_id", "created_at"],
        )

    if op.get_bind().dialect.name == "sqlite":
        op.execute(
            """
            CREATE TRIGGER IF NOT EXISTS inventory_movements_no_update
            BEFORE UPDATE ON inventory_movements
            BEGIN
              SELECT RAISE(ABORT, 'inventory movements are append-only');
            END
            """
        )
        op.execute(
            """
            CREATE TRIGGER IF NOT EXISTS inventory_movements_no_delete
            BEFORE DELETE ON inventory_movements
            BEGIN
              SELECT RAISE(ABORT, 'inventory movements are append-only');
            END
            """
        )


def downgrade() -> None:
    # Pilot migrations are intentionally additive; local histories are never erased.
    pass
