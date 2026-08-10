"""Forwarder 1.9.1 source, customer, and canonical location persistence.

Revision ID: 20260819_v191_acceptance_corrections
Revises: 20260818_immutable_fx_provenance
"""
from alembic import op
import sqlalchemy as sa


revision = "20260819_v191_acceptance_corrections"
down_revision = "20260818_immutable_fx_provenance"
branch_labels = None
depends_on = None

BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
SOURCE_SHAPE = (
    "(source_type = 'accepted_quote' "
    "AND shipment_request_id IS NOT NULL "
    "AND accepted_quote_id IS NOT NULL) OR "
    "(source_type = 'direct' "
    "AND customer_id IS NOT NULL "
    "AND shipment_request_id IS NULL "
    "AND accepted_quote_id IS NULL)"
)


def _is_postgresql(connection) -> bool:
    return connection.dialect.name == "postgresql"


def _scalar(connection, statement: str) -> int:
    return int(connection.execute(sa.text(statement)).scalar_one())


def upgrade():
    connection = op.get_bind()
    if _is_postgresql(connection):
        connection.execute(sa.text("SET LOCAL lock_timeout = '5s'"))
        connection.execute(sa.text("SET LOCAL statement_timeout = '5min'"))

    with op.batch_alter_table("operational_shipment") as batch:
        batch.add_column(sa.Column("source_type", sa.String(24), nullable=True))
        batch.add_column(sa.Column("customer_id", BIGINT, nullable=True))
        batch.create_foreign_key(
            "fk_operational_shipment_customer_id",
            "customer",
            ["customer_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_index(
            "ix_operational_shipment_customer_id", ["customer_id"]
        )
        batch.create_index(
            "ix_operational_shipment_org_customer_status",
            ["organization_id", "customer_id", "lifecycle_status"],
        )

    location_columns = (
        ("origin_country_id", "country", "fk_shipment_request_origin_country_id"),
        (
            "origin_international_city_id",
            "international_city",
            "fk_shipment_request_origin_international_city_id",
        ),
        ("dest_country_id", "country", "fk_shipment_request_dest_country_id"),
        (
            "dest_international_city_id",
            "international_city",
            "fk_shipment_request_dest_international_city_id",
        ),
    )
    with op.batch_alter_table("shipment_request") as batch:
        for column, target, fk_name in location_columns:
            batch.add_column(sa.Column(column, BIGINT, nullable=True))
            batch.create_foreign_key(
                fk_name,
                target,
                [column],
                ["id"],
                ondelete="RESTRICT",
            )
            batch.create_index(f"ix_shipment_request_{column}", [column])

    incomplete_lineage = _scalar(
        connection,
        "SELECT count(*) FROM operational_shipment "
        "WHERE shipment_request_id IS NULL OR accepted_quote_id IS NULL",
    )
    if incomplete_lineage:
        raise RuntimeError(
            "Upgrade refused: existing OperationalShipment commercial lineage is incomplete"
        )

    connection.execute(
        sa.text(
            "UPDATE operational_shipment SET source_type = 'accepted_quote' "
            "WHERE source_type IS NULL"
        )
    )
    if _is_postgresql(connection):
        connection.execute(
            sa.text(
                "UPDATE operational_shipment AS os SET customer_id = sr.customer_id "
                "FROM shipment_request AS sr "
                "WHERE os.shipment_request_id = sr.id "
                "AND os.customer_id IS NULL AND sr.customer_id IS NOT NULL"
            )
        )
    else:
        connection.execute(
            sa.text(
                "UPDATE operational_shipment SET customer_id = ("
                "SELECT sr.customer_id FROM shipment_request AS sr "
                "WHERE sr.id = operational_shipment.shipment_request_id"
                ") WHERE customer_id IS NULL AND EXISTS ("
                "SELECT 1 FROM shipment_request AS sr "
                "WHERE sr.id = operational_shipment.shipment_request_id "
                "AND sr.customer_id IS NOT NULL)"
            )
        )

    null_sources = _scalar(
        connection,
        "SELECT count(*) FROM operational_shipment WHERE source_type IS NULL",
    )
    if null_sources:
        raise RuntimeError("Upgrade refused: source_type backfill was incomplete")

    with op.batch_alter_table("operational_shipment") as batch:
        batch.alter_column(
            "source_type", existing_type=sa.String(24), nullable=False
        )
        batch.alter_column(
            "shipment_request_id", existing_type=BIGINT, nullable=True
        )
        batch.alter_column(
            "accepted_quote_id", existing_type=BIGINT, nullable=True
        )

    if _is_postgresql(connection):
        connection.execute(
            sa.text(
                "ALTER TABLE operational_shipment ADD CONSTRAINT "
                "ck_operational_shipment_source_shape CHECK ("
                + SOURCE_SHAPE
                + ") NOT VALID"
            )
        )
        connection.execute(
            sa.text(
                "ALTER TABLE operational_shipment VALIDATE CONSTRAINT "
                "ck_operational_shipment_source_shape"
            )
        )
    else:
        with op.batch_alter_table("operational_shipment") as batch:
            batch.create_check_constraint(
                "ck_operational_shipment_source_shape", SOURCE_SHAPE
            )


def downgrade():
    connection = op.get_bind()
    if _is_postgresql(connection):
        connection.execute(sa.text("SET LOCAL lock_timeout = '5s'"))
        connection.execute(sa.text("SET LOCAL statement_timeout = '5min'"))

    if _scalar(
        connection,
        "SELECT count(*) FROM operational_shipment WHERE source_type = 'direct'",
    ):
        raise RuntimeError("Downgrade refused: direct OperationalShipment rows exist")
    if _scalar(
        connection,
        "SELECT count(*) FROM operational_shipment "
        "WHERE shipment_request_id IS NULL OR accepted_quote_id IS NULL",
    ):
        raise RuntimeError(
            "Downgrade refused: v1.9.0 commercial lineage cannot be restored safely"
        )
    if _scalar(
        connection,
        "SELECT count(*) FROM shipment_request WHERE "
        "origin_country_id IS NOT NULL OR origin_international_city_id IS NOT NULL "
        "OR dest_country_id IS NOT NULL OR dest_international_city_id IS NOT NULL",
    ):
        raise RuntimeError(
            "Downgrade refused: canonical international location data would be lost"
        )

    with op.batch_alter_table("operational_shipment") as batch:
        batch.drop_constraint(
            "ck_operational_shipment_source_shape", type_="check"
        )
        batch.alter_column(
            "accepted_quote_id", existing_type=BIGINT, nullable=False
        )
        batch.alter_column(
            "shipment_request_id", existing_type=BIGINT, nullable=False
        )

    location_columns = (
        ("dest_international_city_id", "fk_shipment_request_dest_international_city_id"),
        ("dest_country_id", "fk_shipment_request_dest_country_id"),
        (
            "origin_international_city_id",
            "fk_shipment_request_origin_international_city_id",
        ),
        ("origin_country_id", "fk_shipment_request_origin_country_id"),
    )
    with op.batch_alter_table("shipment_request") as batch:
        for column, fk_name in location_columns:
            batch.drop_index(f"ix_shipment_request_{column}")
            batch.drop_constraint(fk_name, type_="foreignkey")
            batch.drop_column(column)

    with op.batch_alter_table("operational_shipment") as batch:
        batch.drop_index("ix_operational_shipment_org_customer_status")
        batch.drop_index("ix_operational_shipment_customer_id")
        batch.drop_constraint(
            "fk_operational_shipment_customer_id", type_="foreignkey"
        )
        batch.drop_column("customer_id")
        batch.drop_column("source_type")
