"""ADR-046 additive Commercial request intent; no historical inference."""
from alembic import op
import sqlalchemy as sa

revision = "20260916_fwd03_transport_intent"
down_revision = "20260916_fwd01_notifications"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("shipment_request", sa.Column("transport_intent", sa.JSON(none_as_null=True), nullable=True))


def downgrade():
    connection = op.get_bind()
    if connection.dialect.name == "postgresql":
        # Serialize the check/drop with writers; refuse before any schema change.
        connection.execute(sa.text("LOCK TABLE shipment_request IN ACCESS EXCLUSIVE MODE"))
    if connection.execute(sa.text("SELECT count(*) FROM shipment_request WHERE transport_intent IS NOT NULL")).scalar():
        raise RuntimeError("Transport intent history exists; retain schema and data for application rollback")
    op.drop_column("shipment_request", "transport_intent")
