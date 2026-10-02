"""Add tenant ownership and file classification to the existing document models."""
from alembic import op
import sqlalchemy as sa

revision = "20261017_document_type_ownership"
down_revision = "20261016_active_route_basis"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("document_definition") as batch:
        batch.add_column(sa.Column("organization_id", sa.BigInteger(), nullable=True))
        batch.create_foreign_key("fk_document_definition_organization", "operational_organization", ["organization_id"], ["id"], ondelete="RESTRICT")
        batch.create_index("ix_document_definition_organization_id", ["organization_id"])
    with op.batch_alter_table("case_document_file") as batch:
        batch.add_column(sa.Column("document_definition_id", sa.BigInteger(), nullable=True))
        batch.create_foreign_key("fk_case_document_file_definition", "document_definition", ["document_definition_id"], ["id"], ondelete="RESTRICT")
        batch.create_index("ix_case_document_file_document_definition_id", ["document_definition_id"])


def downgrade():
    connection = op.get_bind()
    if connection.execute(sa.text("SELECT count(*) FROM document_definition WHERE organization_id IS NOT NULL")).scalar() or connection.execute(sa.text("SELECT count(*) FROM case_document_file WHERE document_definition_id IS NOT NULL")).scalar():
        raise RuntimeError("Document type ownership evidence exists; destructive downgrade is refused.")
    with op.batch_alter_table("case_document_file") as batch:
        batch.drop_index("ix_case_document_file_document_definition_id")
        batch.drop_constraint("fk_case_document_file_definition", type_="foreignkey")
        batch.drop_column("document_definition_id")
    with op.batch_alter_table("document_definition") as batch:
        batch.drop_index("ix_document_definition_organization_id")
        batch.drop_constraint("fk_document_definition_organization", type_="foreignkey")
        batch.drop_column("organization_id")
