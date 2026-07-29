"""Add case document management foundation.

Revision ID: 20260804_case_documents
Revises: 20260803_expert_sla
"""
from alembic import op
import sqlalchemy as sa

revision = "20260804_case_documents"
down_revision = "20260803_expert_sla"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("document_definition",
        sa.Column("id", sa.BigInteger(), primary_key=True), sa.Column("code", sa.String(64), nullable=False),
        sa.Column("title", sa.String(200), nullable=False), sa.Column("description", sa.Text()),
        sa.Column("is_required", sa.Boolean(), nullable=False), sa.Column("allowed_formats", sa.Text(), nullable=False),
        sa.Column("max_file_size_bytes", sa.BigInteger(), nullable=False), sa.Column("max_active_file_count", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("applicability_scope", sa.String(20), nullable=False), sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.BigInteger(), sa.ForeignKey("expert_user.id", ondelete="SET NULL")),
        sa.Column("updated_by", sa.BigInteger(), sa.ForeignKey("expert_user.id", ondelete="SET NULL")),
        sa.CheckConstraint("max_file_size_bytes > 0", name="ck_document_definition_max_size"),
        sa.CheckConstraint("max_active_file_count > 0", name="ck_document_definition_max_count"),
        sa.CheckConstraint("applicability_scope IN ('all', 'domestic', 'international')", name="ck_document_definition_scope"))
    op.create_index("ix_document_definition_code", "document_definition", ["code"], unique=True)
    op.create_index("ix_document_definition_is_active", "document_definition", ["is_active"])
    op.create_table("case_document_requirement",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("shipment_request_id", sa.BigInteger(), sa.ForeignKey("shipment_request.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_definition_id", sa.BigInteger(), sa.ForeignKey("document_definition.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_definition_code", sa.String(64), nullable=False), sa.Column("source_definition_revision", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False), sa.Column("description", sa.Text()), sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("allowed_formats", sa.Text(), nullable=False), sa.Column("max_file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("max_active_file_count", sa.Integer(), nullable=False), sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("applied_at", sa.DateTime(), nullable=False), sa.Column("applied_by", sa.BigInteger(), sa.ForeignKey("expert_user.id", ondelete="SET NULL")),
        sa.UniqueConstraint("shipment_request_id", "source_definition_id", "source_definition_revision", name="uq_case_document_requirement_source_revision"))
    op.create_index("ix_case_document_requirement_shipment_request_id", "case_document_requirement", ["shipment_request_id"])
    op.create_index("ix_case_document_requirement_source_definition_id", "case_document_requirement", ["source_definition_id"])
    op.create_table("case_document_file",
        sa.Column("id", sa.BigInteger(), primary_key=True), sa.Column("shipment_request_id", sa.BigInteger(), sa.ForeignKey("shipment_request.id", ondelete="CASCADE"), nullable=False),
        sa.Column("case_requirement_id", sa.BigInteger(), sa.ForeignKey("case_document_requirement.id", ondelete="RESTRICT")),
        sa.Column("is_miscellaneous", sa.Boolean(), nullable=False), sa.Column("custom_title", sa.String(200)), sa.Column("description", sa.Text()),
        sa.Column("original_filename", sa.String(255), nullable=False), sa.Column("safe_download_filename", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False, unique=True), sa.Column("canonical_extension", sa.String(10), nullable=False),
        sa.Column("detected_mime_type", sa.String(100), nullable=False), sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256_hash", sa.String(64), nullable=False), sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("uploaded_by", sa.BigInteger(), sa.ForeignKey("expert_user.id", ondelete="SET NULL")), sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column("superseded_at", sa.DateTime()), sa.Column("superseded_by", sa.BigInteger(), sa.ForeignKey("case_document_file.id", ondelete="SET NULL")),
        sa.Column("deleted_at", sa.DateTime()), sa.Column("deleted_by", sa.BigInteger(), sa.ForeignKey("expert_user.id", ondelete="SET NULL")), sa.Column("deletion_reason", sa.Text()),
        sa.CheckConstraint("status IN ('active', 'superseded', 'deleted')", name="ck_case_document_file_status"),
        sa.CheckConstraint("(is_miscellaneous = true AND case_requirement_id IS NULL AND custom_title IS NOT NULL) OR (is_miscellaneous = false AND case_requirement_id IS NOT NULL)", name="ck_case_document_file_requirement"),
        sa.UniqueConstraint("case_requirement_id", "version_number", name="uq_case_document_file_requirement_version"))
    for column in ("shipment_request_id", "case_requirement_id", "is_miscellaneous", "status"):
        op.create_index(f"ix_case_document_file_{column}", "case_document_file", [column])
    op.create_table("document_audit_event",
        sa.Column("id", sa.BigInteger(), primary_key=True), sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("actor_id", sa.BigInteger(), sa.ForeignKey("expert_user.id", ondelete="SET NULL")),
        sa.Column("shipment_request_id", sa.BigInteger(), sa.ForeignKey("shipment_request.id", ondelete="SET NULL")),
        sa.Column("definition_id", sa.BigInteger(), sa.ForeignKey("document_definition.id", ondelete="SET NULL")),
        sa.Column("document_file_id", sa.BigInteger(), sa.ForeignKey("case_document_file.id", ondelete="SET NULL")),
        sa.Column("details", sa.Text()), sa.Column("created_at", sa.DateTime(), nullable=False))
    for column in ("event_type", "actor_id", "shipment_request_id", "created_at"):
        op.create_index(f"ix_document_audit_event_{column}", "document_audit_event", [column])


def downgrade():
    op.drop_table("document_audit_event")
    op.drop_table("case_document_file")
    op.drop_table("case_document_requirement")
    op.drop_table("document_definition")
