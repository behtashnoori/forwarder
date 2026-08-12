"""Expand canonical MT-1 ownership envelopes without assigning legacy rows.

Revision ID: 20260823_mt1_ownership_expand
Revises: 20260822_mt1c1_census_fence
"""
from alembic import op
import sqlalchemy as sa


revision = "20260823_mt1_ownership_expand"
down_revision = "20260822_mt1c1_census_fence"
branch_labels = None
depends_on = None

BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

ROOTS = ("shipment_request", "customer")
REQUEST_CHILDREN = (
    ("shipment_request_log", "shipment_request_id"),
    ("shipment_tracking", "shipment_request_id"),
    ("expert_quote", "shipment_request_id"),
    ("expert_console_log", "shipment_request_id"),
    ("expert_console_message", "shipment_request_id"),
    ("expert_console_notification", "shipment_request_id"),
    ("referral_assignment_log", "request_id"),
    ("case_document_requirement", "shipment_request_id"),
    ("case_document_file", "shipment_request_id"),
)
CUSTOMER_CHILDREN = (
    ("customer_contact", "customer_id"),
    ("opportunity", "customer_id"),
)


def _add_owner(table):
    op.add_column(table, sa.Column("operational_organization_id", BIGINT, nullable=True))
    op.create_index(f"ix_{table}_operational_org", table, ["operational_organization_id"])
    op.create_foreign_key(
        f"fk_{table}_operational_org", table, "operational_organization",
        ["operational_organization_id"], ["id"], ondelete="RESTRICT",
    )


def _add_child(table, parent_column, parent_table):
    _add_owner(table)
    op.create_foreign_key(
        f"fk_{table}_{parent_table}_same_org", table, parent_table,
        [parent_column, "operational_organization_id"],
        ["id", "operational_organization_id"], ondelete="RESTRICT",
    )


def upgrade():
    for table in ROOTS:
        _add_owner(table)
        op.add_column(table, sa.Column("ownership_scope", sa.String(24), nullable=True))
        op.create_check_constraint(
            f"ck_{table}_ownership_envelope", table,
            "ownership_scope IS NULL OR "
            "(ownership_scope = 'TENANT' AND operational_organization_id IS NOT NULL) OR "
            "(ownership_scope IN ('INTAKE','LEGACY_QUARANTINED') AND operational_organization_id IS NULL)",
        )
        op.create_unique_constraint(
            f"uq_{table}_id_operational_org", table, ["id", "operational_organization_id"]
        )

    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
            CREATE FUNCTION mt1_reject_ambiguous_new_root() RETURNS trigger AS $$
            BEGIN
              IF NEW.ownership_scope IS NULL THEN
                RAISE EXCEPTION 'new % row requires explicit ownership_scope', TG_TABLE_NAME
                  USING ERRCODE = '23514';
              END IF;
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
        """)
        for table in ROOTS:
            op.execute(
                f"CREATE TRIGGER trg_{table}_explicit_ownership "
                f"BEFORE INSERT ON {table} FOR EACH ROW "
                "EXECUTE FUNCTION mt1_reject_ambiguous_new_root()"
            )

    # ExpertQuote already acquired this column in the operational vertical slice.
    for table, parent_column in REQUEST_CHILDREN:
        if table == "expert_quote":
            if op.get_bind().dialect.name == "postgresql":
                # Existing quote ownership predates canonical request ownership.
                # NOT VALID enforces new writes without falsely certifying legacy rows.
                op.execute(
                    "ALTER TABLE expert_quote ADD CONSTRAINT fk_expert_quote_request_same_org "
                    "FOREIGN KEY (shipment_request_id, operational_organization_id) "
                    "REFERENCES shipment_request (id, operational_organization_id) NOT VALID"
                )
            else:
                op.create_foreign_key(
                    "fk_expert_quote_request_same_org", table, "shipment_request",
                    [parent_column, "operational_organization_id"],
                    ["id", "operational_organization_id"], ondelete="RESTRICT",
                )
        else:
            _add_child(table, parent_column, "shipment_request")
    for table, parent_column in CUSTOMER_CHILDREN:
        _add_child(table, parent_column, "customer")

    op.add_column("document_audit_event", sa.Column("scope_type", sa.String(16), nullable=True))
    _add_owner("document_audit_event")
    op.create_check_constraint(
        "ck_document_audit_event_scope", "document_audit_event",
        "scope_type IS NULL OR "
        "(scope_type = 'TENANT' AND operational_organization_id IS NOT NULL) OR "
        "(scope_type = 'PLATFORM' AND operational_organization_id IS NULL)",
    )
    op.create_foreign_key(
        "fk_document_audit_event_request_same_org", "document_audit_event", "shipment_request",
        ["shipment_request_id", "operational_organization_id"],
        ["id", "operational_organization_id"], ondelete="RESTRICT",
    )


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        for table in ROOTS:
            op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_explicit_ownership ON {table}")
        op.execute("DROP FUNCTION IF EXISTS mt1_reject_ambiguous_new_root()")
    op.drop_constraint("fk_document_audit_event_request_same_org", "document_audit_event", type_="foreignkey")
    op.drop_constraint("ck_document_audit_event_scope", "document_audit_event", type_="check")
    op.drop_constraint("fk_document_audit_event_operational_org", "document_audit_event", type_="foreignkey")
    op.drop_index("ix_document_audit_event_operational_org", table_name="document_audit_event")
    op.drop_column("document_audit_event", "operational_organization_id")
    op.drop_column("document_audit_event", "scope_type")
    for table, _ in reversed(CUSTOMER_CHILDREN):
        op.drop_constraint(f"fk_{table}_customer_same_org", table, type_="foreignkey")
        op.drop_constraint(f"fk_{table}_operational_org", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_operational_org", table_name=table)
        op.drop_column(table, "operational_organization_id")
    for table, _ in reversed(REQUEST_CHILDREN):
        constraint_name = (
            "fk_expert_quote_request_same_org" if table == "expert_quote"
            else f"fk_{table}_shipment_request_same_org"
        )
        op.drop_constraint(constraint_name, table, type_="foreignkey")
        if table != "expert_quote":
            op.drop_constraint(f"fk_{table}_operational_org", table, type_="foreignkey")
            op.drop_index(f"ix_{table}_operational_org", table_name=table)
            op.drop_column(table, "operational_organization_id")
    for table in reversed(ROOTS):
        op.drop_constraint(f"uq_{table}_id_operational_org", table, type_="unique")
        op.drop_constraint(f"ck_{table}_ownership_envelope", table, type_="check")
        op.drop_column(table, "ownership_scope")
        op.drop_constraint(f"fk_{table}_operational_org", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_operational_org", table_name=table)
        op.drop_column(table, "operational_organization_id")
