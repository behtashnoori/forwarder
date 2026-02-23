"""Ensure expert_quote table exists (idempotent). Creates table only if missing; no drop, no data loss.

Revision ID: 20250223_ensure_quote
Revises: 20250223_quote_fix
Create Date: 2025-02-23

"""
from alembic import op

revision = "20250223_ensure_quote"
down_revision = "20250223_quote_fix"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    dialect_name = conn.dialect.name

    if dialect_name == "postgresql":
        op.execute("""
            CREATE TABLE IF NOT EXISTS expert_quote (
                id BIGSERIAL PRIMARY KEY,
                shipment_request_id BIGINT NOT NULL REFERENCES shipment_request(id) ON DELETE CASCADE,
                amount BIGINT NOT NULL,
                currency VARCHAR(10) NOT NULL DEFAULT 'IRR',
                note TEXT,
                valid_until DATE,
                created_by_expert_id BIGINT NOT NULL REFERENCES expert_user(id),
                created_at TIMESTAMP NOT NULL
            )
        """)
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_expert_quote_request_id ON expert_quote (shipment_request_id)"
        )
    elif dialect_name == "sqlite":
        op.execute("""
            CREATE TABLE IF NOT EXISTS expert_quote (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                shipment_request_id INTEGER NOT NULL REFERENCES shipment_request(id) ON DELETE CASCADE,
                amount INTEGER NOT NULL,
                currency VARCHAR(10) NOT NULL DEFAULT 'IRR',
                note TEXT,
                valid_until DATE,
                created_by_expert_id INTEGER NOT NULL REFERENCES expert_user(id),
                created_at TIMESTAMP NOT NULL
            )
        """)
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_expert_quote_request_id ON expert_quote (shipment_request_id)"
        )
    else:
        raise RuntimeError("Unsupported dialect for expert_quote ensure migration: %s" % dialect_name)


def downgrade():
    op.execute("DROP TABLE IF EXISTS expert_quote")
