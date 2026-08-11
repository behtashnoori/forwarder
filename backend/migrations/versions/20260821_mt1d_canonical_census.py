"""Add MT-1D canonical identity and atomic census publication tables.

Revision ID: 20260821_mt1d_canonical_census
Revises: 20260820_mt1c_quarantine_runtime
"""
from alembic import op
import sqlalchemy as sa


revision = "20260821_mt1d_canonical_census"
down_revision = "20260820_mt1c_quarantine_runtime"
branch_labels = None
depends_on = None

BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
IMMUTABLE_TABLES = (
    "ownership_census",
    "ownership_census_scope",
    "ownership_decision",
    "ownership_census_activation",
)


def upgrade():
    op.create_table(
        "ownership_census",
        sa.Column("census_id", sa.String(64), primary_key=True),
        sa.Column("analysis_version", sa.String(64), nullable=False),
        sa.Column("publication_order", sa.BigInteger(), nullable=False),
        sa.Column("manifest_fingerprint", sa.String(64), nullable=False),
        sa.Column("source_fingerprint", sa.String(64), nullable=False),
        sa.Column("previous_census_id", sa.String(64), nullable=True),
        sa.Column("publisher", sa.String(128), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("publication_order >= 1", name="ck_ownership_census_order"),
        sa.CheckConstraint(
            "length(manifest_fingerprint) = 64",
            name="ck_ownership_census_manifest_fingerprint",
        ),
        sa.CheckConstraint(
            "length(source_fingerprint) = 64",
            name="ck_ownership_census_source_fingerprint",
        ),
        sa.ForeignKeyConstraint(
            ["previous_census_id"], ["ownership_census.census_id"],
            name="fk_ownership_census_previous",
        ),
        sa.UniqueConstraint("publication_order", name="uq_ownership_census_order"),
        sa.UniqueConstraint(
            "census_id", "publication_order", name="uq_ownership_census_id_order"
        ),
        sa.UniqueConstraint(
            "manifest_fingerprint", name="uq_ownership_census_manifest_fingerprint"
        ),
    )
    op.create_table(
        "ownership_census_scope",
        sa.Column("census_id", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(80), nullable=False),
        sa.Column("expected_decision_count", sa.BigInteger(), nullable=False),
        sa.Column("evidence_fingerprint", sa.String(64), nullable=False),
        sa.CheckConstraint(
            "expected_decision_count >= 0", name="ck_ownership_census_scope_count"
        ),
        sa.CheckConstraint(
            "length(evidence_fingerprint) = 64",
            name="ck_ownership_census_scope_fingerprint",
        ),
        sa.ForeignKeyConstraint(
            ["census_id"], ["ownership_census.census_id"],
            name="fk_ownership_census_scope_census",
        ),
        sa.PrimaryKeyConstraint("census_id", "resource_type", name="pk_ownership_census_scope"),
    )
    op.create_table(
        "ownership_decision",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("census_id", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(80), nullable=False),
        sa.Column("resource_key_hash", sa.String(64), nullable=False),
        sa.Column("resource_key_payload", sa.Text(), nullable=False),
        sa.Column("scalar_integer_id", sa.BigInteger(), nullable=True),
        sa.Column("decision_version", sa.BigInteger(), nullable=False),
        sa.Column("classification", sa.String(32), nullable=False),
        sa.Column("enforcement_state", sa.String(16), nullable=False),
        sa.Column("source_fingerprint", sa.String(64), nullable=False),
        sa.Column("effective_order", sa.BigInteger(), nullable=False),
        sa.Column("effective_at", sa.DateTime(), nullable=False),
        sa.Column("supersedes_decision_id", BIGINT, nullable=True),
        sa.Column("root_resource_type", sa.String(80), nullable=False),
        sa.Column("root_resource_key_hash", sa.String(64), nullable=False),
        sa.Column("root_resource_key_payload", sa.Text(), nullable=False),
        sa.CheckConstraint("decision_version >= 1", name="ck_ownership_decision_version"),
        sa.CheckConstraint("effective_order >= 1", name="ck_ownership_decision_order"),
        sa.CheckConstraint(
            "classification IN ('DETERMINISTIC','CONFLICT','UNRESOLVED','INVALID_LINEAGE')",
            name="ck_ownership_decision_classification_v2",
        ),
        sa.CheckConstraint(
            "enforcement_state IN ('CLEAR','QUARANTINED')",
            name="ck_ownership_decision_enforcement",
        ),
        sa.CheckConstraint(
            "enforcement_state <> 'CLEAR' OR classification = 'DETERMINISTIC'",
            name="ck_ownership_decision_clear_deterministic",
        ),
        sa.CheckConstraint(
            "length(resource_key_hash) = 64 AND length(root_resource_key_hash) = 64 "
            "AND length(source_fingerprint) = 64",
            name="ck_ownership_decision_hash_lengths",
        ),
        sa.ForeignKeyConstraint(
            ["census_id"], ["ownership_census.census_id"],
            name="fk_ownership_decision_census",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_decision_id"], ["ownership_decision.id"],
            name="fk_ownership_decision_supersedes",
        ),
        sa.UniqueConstraint(
            "census_id", "resource_type", "resource_key_hash",
            name="uq_ownership_decision_census_resource",
        ),
        sa.UniqueConstraint(
            "resource_type", "resource_key_hash", "decision_version",
            name="uq_ownership_decision_resource_version",
        ),
    )
    op.create_index(
        "ix_ownership_decision_active_scalar",
        "ownership_decision",
        ["census_id", "resource_type", "scalar_integer_id"],
    )
    op.create_index(
        "ix_ownership_decision_active_key",
        "ownership_decision",
        ["census_id", "resource_type", "resource_key_hash"],
    )
    op.create_table(
        "ownership_active_census",
        sa.Column("singleton_id", sa.Integer(), primary_key=True),
        sa.Column("census_id", sa.String(64), nullable=False),
        sa.Column("publication_order", sa.BigInteger(), nullable=False),
        sa.Column("cache_version", sa.BigInteger(), nullable=False),
        sa.Column("cache_token", sa.String(36), nullable=False),
        sa.Column("activated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("singleton_id = 1", name="ck_ownership_active_singleton"),
        sa.CheckConstraint("publication_order >= 1", name="ck_ownership_active_order"),
        sa.CheckConstraint("cache_version >= 1", name="ck_ownership_active_cache_version"),
        sa.ForeignKeyConstraint(
            ["census_id", "publication_order"],
            ["ownership_census.census_id", "ownership_census.publication_order"],
            name="fk_ownership_active_census_order",
        ),
        sa.UniqueConstraint("census_id", name="uq_ownership_active_census_id"),
        sa.UniqueConstraint("cache_token", name="uq_ownership_active_cache_token"),
    )
    op.create_table(
        "ownership_census_activation",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("census_id", sa.String(64), nullable=False),
        sa.Column("previous_census_id", sa.String(64), nullable=True),
        sa.Column("cache_version", sa.BigInteger(), nullable=False),
        sa.Column("cache_token", sa.String(36), nullable=False),
        sa.Column("activated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["census_id"], ["ownership_census.census_id"],
            name="fk_ownership_census_activation_census",
        ),
        sa.ForeignKeyConstraint(
            ["previous_census_id"], ["ownership_census.census_id"],
            name="fk_ownership_census_activation_previous",
        ),
        sa.UniqueConstraint("census_id", name="uq_ownership_activation_census"),
        sa.UniqueConstraint("cache_version", name="uq_ownership_activation_cache_version"),
        sa.UniqueConstraint("cache_token", name="uq_ownership_activation_cache_token"),
    )

    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
            CREATE FUNCTION mt1d_reject_history_rewrite() RETURNS trigger
            LANGUAGE plpgsql AS $$
            BEGIN
                RAISE EXCEPTION 'ownership census history is append-only';
            END;
            $$
        """)
        for table_name in IMMUTABLE_TABLES:
            op.execute(f"""
                CREATE TRIGGER trg_{table_name}_append_only
                BEFORE UPDATE OR DELETE ON {table_name}
                FOR EACH ROW EXECUTE FUNCTION mt1d_reject_history_rewrite()
            """)
        op.execute("""
            CREATE FUNCTION mt1d_validate_active_transition() RETURNS trigger
            LANGUAGE plpgsql AS $$
            BEGIN
                IF TG_OP = 'DELETE' THEN
                    RAISE EXCEPTION 'active census authority cannot be deleted';
                END IF;
                IF NEW.cache_version <> OLD.cache_version + 1
                   OR NEW.cache_token = OLD.cache_token
                   OR NEW.census_id = OLD.census_id
                   OR NEW.publication_order <= OLD.publication_order THEN
                    RAISE EXCEPTION 'active census transition must rotate version and token';
                END IF;
                RETURN NEW;
            END;
            $$
        """)
        op.execute("""
            CREATE TRIGGER trg_ownership_active_census_transition
            BEFORE UPDATE OR DELETE ON ownership_active_census
            FOR EACH ROW EXECUTE FUNCTION mt1d_validate_active_transition()
        """)
        for table_name in (*IMMUTABLE_TABLES, "ownership_active_census"):
            op.execute(
                f"REVOKE INSERT, UPDATE, DELETE ON {table_name} FROM PUBLIC"
            )


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS trg_ownership_active_census_transition "
            "ON ownership_active_census"
        )
        op.execute("DROP FUNCTION IF EXISTS mt1d_validate_active_transition()")
        for table_name in reversed(IMMUTABLE_TABLES):
            op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_append_only ON {table_name}")
        op.execute("DROP FUNCTION IF EXISTS mt1d_reject_history_rewrite()")
    op.drop_table("ownership_census_activation")
    op.drop_table("ownership_active_census")
    op.drop_index("ix_ownership_decision_active_key", table_name="ownership_decision")
    op.drop_index("ix_ownership_decision_active_scalar", table_name="ownership_decision")
    op.drop_table("ownership_decision")
    op.drop_table("ownership_census_scope")
    op.drop_table("ownership_census")
