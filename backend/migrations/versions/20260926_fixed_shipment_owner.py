"""Enforce ADR-047 fixed OperationalShipment responsible Expert ownership.

Revision ID: 20260926_fixed_shipment_responsible_expert
Revises: 20260925_quote_communication
"""

from alembic import op
import sqlalchemy as sa


revision = "20260926_fixed_shipment_responsible_expert"
down_revision = "20260925_quote_communication"
branch_labels = None
depends_on = None

BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
TRIGGER_NAME = "trg_operational_shipment_fixed_owner"
FUNCTION_NAME = "prevent_operational_shipment_owner_change"


def _owner_is_historically_valid(bind, owner_id: int, organization_id: int) -> bool:
    row = bind.execute(
        sa.text(
            "SELECT eu.authority, om.id AS membership_id "
            "FROM expert_user eu "
            "LEFT JOIN operational_membership om "
            "ON om.user_id = eu.id AND om.organization_id = :organization_id "
            "WHERE eu.id = :owner_id"
        ),
        {"owner_id": owner_id, "organization_id": organization_id},
    ).mappings().one_or_none()
    return bool(
        row
        and str(row["authority"] or "").upper() == "EXPERT"
        and row["membership_id"] is not None
    )


def _accepted_quote_owner(bind, shipment) -> tuple[int | None, str | None]:
    if shipment["accepted_quote_id"] is None or shipment["shipment_request_id"] is None:
        return None, "MISSING_ACCEPTED_QUOTE_LINEAGE"
    quote = bind.execute(
        sa.text(
            "SELECT id, shipment_request_id, operational_organization_id, "
            "created_by_expert_id, customer_response "
            "FROM expert_quote WHERE id = :quote_id"
        ),
        {"quote_id": shipment["accepted_quote_id"]},
    ).mappings().one_or_none()
    if quote is None:
        return None, "MISSING_ACCEPTED_QUOTE"
    if (
        quote["shipment_request_id"] != shipment["shipment_request_id"]
        or quote["operational_organization_id"] != shipment["organization_id"]
        or quote["customer_response"] != "accepted"
    ):
        return None, "CONFLICTING_ACCEPTED_QUOTE_LINEAGE"
    owner_id = quote["created_by_expert_id"]
    if owner_id is None or not _owner_is_historically_valid(
        bind, owner_id, shipment["organization_id"]
    ):
        return None, "INVALID_ACCEPTED_QUOTE_ISSUER"
    return int(owner_id), None


def _validated_reconciliation(bind) -> list[tuple[int, int]]:
    shipments = bind.execute(
        sa.text(
            "SELECT id, organization_id, source_type, shipment_request_id, "
            "accepted_quote_id, primary_responsible_expert_id "
            "FROM operational_shipment ORDER BY id"
        )
    ).mappings().all()
    repairs: list[tuple[int, int]] = []
    issues: list[str] = []

    for shipment in shipments:
        shipment_id = int(shipment["id"])
        current_owner = shipment["primary_responsible_expert_id"]
        source_type = shipment["source_type"]
        if source_type == "accepted_quote":
            authoritative_owner, reason = _accepted_quote_owner(bind, shipment)
            if reason:
                issues.append(f"{shipment_id}:{reason}")
                continue
            if current_owner is None:
                repairs.append((shipment_id, int(authoritative_owner)))
            elif int(current_owner) != int(authoritative_owner):
                issues.append(f"{shipment_id}:PERSISTED_OWNER_CONFLICT")
        elif source_type == "direct":
            if current_owner is None:
                issues.append(f"{shipment_id}:DIRECT_OWNER_MISSING")
            elif not _owner_is_historically_valid(
                bind, int(current_owner), int(shipment["organization_id"])
            ):
                issues.append(f"{shipment_id}:DIRECT_OWNER_INVALID")
        else:
            issues.append(f"{shipment_id}:UNKNOWN_SOURCE_TYPE")

    if issues:
        raise RuntimeError(
            "ADR-047 owner reconciliation refused; adjudication required for "
            "shipment identifiers/reasons: " + ",".join(issues)
        )
    return repairs


def _create_write_once_guard(bind) -> None:
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                f"CREATE FUNCTION {FUNCTION_NAME}() RETURNS trigger "
                "LANGUAGE plpgsql AS $$ "
                "BEGIN "
                "IF NEW.primary_responsible_expert_id IS DISTINCT FROM "
                "OLD.primary_responsible_expert_id THEN "
                "RAISE EXCEPTION 'OperationalShipment responsible Expert is immutable' "
                "USING ERRCODE = '23514'; "
                "END IF; "
                "RETURN NEW; "
                "END; $$"
            )
        )
        op.execute(
            sa.text(
                f"CREATE TRIGGER {TRIGGER_NAME} BEFORE UPDATE OF "
                "primary_responsible_expert_id ON operational_shipment "
                f"FOR EACH ROW EXECUTE FUNCTION {FUNCTION_NAME}()"
            )
        )
    elif bind.dialect.name == "sqlite":
        op.execute(
            sa.text(
                f"CREATE TRIGGER {TRIGGER_NAME} BEFORE UPDATE OF "
                "primary_responsible_expert_id ON operational_shipment "
                "FOR EACH ROW WHEN NEW.primary_responsible_expert_id IS NOT "
                "OLD.primary_responsible_expert_id BEGIN "
                "SELECT RAISE(ABORT, 'OperationalShipment responsible Expert is immutable'); "
                "END"
            )
        )
    else:
        raise RuntimeError(
            "ADR-047 owner immutability migration supports PostgreSQL and SQLite only"
        )


def _drop_write_once_guard(bind) -> None:
    op.execute(sa.text(f"DROP TRIGGER IF EXISTS {TRIGGER_NAME}" + (
        " ON operational_shipment" if bind.dialect.name == "postgresql" else ""
    )))
    if bind.dialect.name == "postgresql":
        op.execute(sa.text(f"DROP FUNCTION IF EXISTS {FUNCTION_NAME}()"))


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        bind.execute(sa.text("LOCK TABLE operational_shipment IN SHARE ROW EXCLUSIVE MODE"))

    repairs = _validated_reconciliation(bind)
    for shipment_id, owner_id in repairs:
        bind.execute(
            sa.text(
                "UPDATE operational_shipment "
                "SET primary_responsible_expert_id = :owner_id "
                "WHERE id = :shipment_id AND primary_responsible_expert_id IS NULL"
            ),
            {"shipment_id": shipment_id, "owner_id": owner_id},
        )

    with op.batch_alter_table("operational_shipment", schema=None) as batch_op:
        batch_op.alter_column(
            "primary_responsible_expert_id",
            existing_type=BIGINT,
            nullable=False,
        )
    _create_write_once_guard(bind)


def downgrade():
    bind = op.get_bind()
    _drop_write_once_guard(bind)
    with op.batch_alter_table("operational_shipment", schema=None) as batch_op:
        batch_op.alter_column(
            "primary_responsible_expert_id",
            existing_type=BIGINT,
            nullable=True,
        )
