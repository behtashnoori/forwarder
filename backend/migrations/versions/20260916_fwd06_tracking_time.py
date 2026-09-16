"""M1: additive occurrence provenance on compatibility tracking updates."""

from alembic import op
import sqlalchemy as sa

revision = "20260916_fwd06_tracking_time"
down_revision = "20260916_fwd05_quote_response"
branch_labels = None
depends_on = None

TABLE = "shipment_transport_unit_update"


def upgrade():
    op.add_column(TABLE, sa.Column("occurred_at_utc", sa.DateTime(timezone=True), nullable=True))
    op.add_column(TABLE, sa.Column("time_input_wall", sa.String(29), nullable=True))
    op.add_column(TABLE, sa.Column("time_input_basis", sa.String(64), nullable=True))
    op.add_column(TABLE, sa.Column("time_input_source", sa.String(32), nullable=True))
    op.add_column(TABLE, sa.Column("time_input_policy", sa.String(64), nullable=True))
    op.create_check_constraint(
        "ck_tracking_time_envelope", TABLE,
        "(occurred_at_utc IS NULL AND time_input_wall IS NULL AND "
        "time_input_basis IS NULL AND time_input_source IS NULL AND time_input_policy IS NULL) "
        "OR (occurred_at_utc IS NOT NULL AND time_input_wall IS NOT NULL AND "
        "time_input_basis IS NOT NULL AND time_input_basis = 'Asia/Tehran' AND time_input_source IS NOT NULL AND "
        "time_input_source = 'manual' AND time_input_policy IS NOT NULL AND "
        "time_input_policy = 'tracking.manual-iran.v1') "
        "OR (occurred_at_utc IS NOT NULL AND time_input_wall IS NOT NULL AND "
        "time_input_basis IS NOT NULL AND time_input_source IS NOT NULL AND "
        "time_input_source = 'offset' AND "
        "time_input_policy IS NULL)",
    )
    if op.get_bind().dialect.name == "postgresql":
        op.create_check_constraint(
            "ck_tracking_time_consistency", TABLE,
            "occurred_at_utc IS NULL OR ("
            "time_input_wall ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(:[0-9]{2}(\\.[0-9]{1,6})?)?$' AND "
            "occurred_at = (occurred_at_utc AT TIME ZONE 'UTC') AND ("
            "(time_input_source = 'manual' AND occurred_at_utc = "
            "(time_input_wall::timestamp AT TIME ZONE 'Asia/Tehran')) OR "
            "(time_input_source = 'offset' AND "
            "time_input_wall ~ 'T[0-9]{2}:[0-9]{2}:[0-9]{2}' AND "
            "time_input_basis ~ '^[+-](0[0-9]|1[0-3]):[0-5][0-9]$|^[+-]14:00$' AND occurred_at_utc = "
            "(time_input_wall || time_input_basis)::timestamptz)))",
        )
        op.execute(sa.text("""
        CREATE FUNCTION fwd06_tracking_time_immutable() RETURNS trigger AS $$
        BEGIN
          IF OLD.occurred_at_utc IS NOT NULL AND (
            NEW.occurred_at_utc IS DISTINCT FROM OLD.occurred_at_utc OR
            NEW.time_input_wall IS DISTINCT FROM OLD.time_input_wall OR
            NEW.time_input_basis IS DISTINCT FROM OLD.time_input_basis OR
            NEW.time_input_source IS DISTINCT FROM OLD.time_input_source OR
            NEW.time_input_policy IS DISTINCT FROM OLD.time_input_policy OR
            NEW.occurred_at IS DISTINCT FROM OLD.occurred_at
          ) THEN
            RAISE EXCEPTION 'FWD-06 time snapshot is immutable';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """))
        op.execute(sa.text("""
        CREATE TRIGGER trg_fwd06_tracking_time_immutable
        BEFORE UPDATE ON shipment_transport_unit_update
        FOR EACH ROW EXECUTE FUNCTION fwd06_tracking_time_immutable()
        """))


def downgrade():
    # Refuse before any DDL: a populated snapshot may never be silently lost.
    count = op.get_bind().execute(sa.text(
        f"SELECT count(*) FROM {TABLE} WHERE occurred_at_utc IS NOT NULL "
        "OR time_input_wall IS NOT NULL OR time_input_basis IS NOT NULL "
        "OR time_input_source IS NOT NULL OR time_input_policy IS NOT NULL"
    )).scalar_one()
    if count:
        raise RuntimeError("FWD-06 time snapshots exist; downgrade refused before DDL")
    if op.get_bind().dialect.name == "postgresql":
        op.execute(sa.text("DROP TRIGGER trg_fwd06_tracking_time_immutable ON shipment_transport_unit_update"))
        op.execute(sa.text("DROP FUNCTION fwd06_tracking_time_immutable()"))
        op.drop_constraint("ck_tracking_time_consistency", TABLE, type_="check")
    op.drop_constraint("ck_tracking_time_envelope", TABLE, type_="check")
    for column in ("time_input_policy", "time_input_source", "time_input_basis", "time_input_wall", "occurred_at_utc"):
        op.drop_column(TABLE, column)
