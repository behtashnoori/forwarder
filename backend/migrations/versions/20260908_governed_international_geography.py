"""Add stable UN/LOCODE identity and provenance to InternationalCity."""
from alembic import op
import sqlalchemy as sa

revision = "20260908_governed_international_geography"
down_revision = "20260907_direct_shipment_responsibility"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("international_city") as batch:
        batch.add_column(sa.Column("un_locode", sa.String(length=5), nullable=True))
        batch.add_column(sa.Column("source_organization", sa.String(length=160), nullable=True))
        batch.add_column(sa.Column("source_reference", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("source_version", sa.String(length=100), nullable=True))
        batch.add_column(sa.Column("dataset_id", sa.String(length=100), nullable=True))
        batch.create_unique_constraint("uq_international_city_country_un_locode", ["country_id", "un_locode"])
        batch.create_check_constraint("ck_international_city_un_locode", "un_locode IS NULL OR (length(un_locode) = 5 AND un_locode = upper(un_locode))")


def downgrade():
    bound = op.get_bind()
    count = bound.execute(sa.text("SELECT count(*) FROM international_city WHERE un_locode IS NOT NULL")).scalar_one()
    if count:
        raise RuntimeError("Downgrade refused: governed UN/LOCODE evidence exists.")
    with op.batch_alter_table("international_city") as batch:
        batch.drop_constraint("ck_international_city_un_locode", type_="check")
        batch.drop_constraint("uq_international_city_country_un_locode", type_="unique")
        batch.drop_column("dataset_id")
        batch.drop_column("source_version")
        batch.drop_column("source_reference")
        batch.drop_column("source_organization")
        batch.drop_column("un_locode")
