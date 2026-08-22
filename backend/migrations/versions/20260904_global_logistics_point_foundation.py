"""Add empty platform Global Logistics Point foundation.

Revision ID: 20260904_global_logistics_point_foundation
Revises: 20260903_external_operational_references
"""

from alembic import op
import sqlalchemy as sa


revision = "20260904_global_logistics_point_foundation"
down_revision = "20260903_external_operational_references"
branch_labels = None
depends_on = None

BIGINT = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade():
    op.create_table(
        "global_logistics_point",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column("public_id", sa.String(36), nullable=False),
        sa.Column("immutable_code", sa.String(64), nullable=False),
        sa.Column(
            "logistics_point_type_id",
            BIGINT,
            sa.ForeignKey("logistics_point_type.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("fa_name", sa.String(160), nullable=False),
        sa.Column("en_name", sa.String(160), nullable=False),
        sa.Column("normalized_name", sa.String(200), nullable=False),
        sa.Column(
            "country_id",
            BIGINT,
            sa.ForeignKey("country.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "province_id",
            BIGINT,
            sa.ForeignKey("province.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "city_id", BIGINT, sa.ForeignKey("city.id", ondelete="RESTRICT")
        ),
        sa.Column(
            "international_city_id",
            BIGINT,
            sa.ForeignKey("international_city.id", ondelete="RESTRICT"),
        ),
        sa.Column("region_name", sa.String(160)),
        sa.Column("city_name", sa.String(160)),
        sa.Column("geography_key", sa.String(240), nullable=False),
        sa.Column("facility_identity_key", sa.String(240), nullable=False),
        sa.Column("short_address", sa.String(500)),
        sa.Column("latitude", sa.Numeric(9, 6)),
        sa.Column("longitude", sa.Numeric(9, 6)),
        sa.Column("timezone_name", sa.String(64)),
        sa.Column("un_locode", sa.String(5)),
        sa.Column("border_pair_key", sa.String(100)),
        sa.Column("border_side", sa.String(16)),
        sa.Column(
            "lifecycle_status",
            sa.String(16),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column(
            "verification_status",
            sa.String(16),
            nullable=False,
            server_default="UNVERIFIED",
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_by",
            BIGINT,
            sa.ForeignKey("expert_user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "updated_by",
            BIGINT,
            sa.ForeignKey("expert_user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.UniqueConstraint("public_id", name="uq_global_logistics_point_public_id"),
        sa.UniqueConstraint(
            "immutable_code", name="uq_global_logistics_point_immutable_code"
        ),
        sa.UniqueConstraint(
            "country_id",
            "logistics_point_type_id",
            "facility_identity_key",
            name="uq_global_logistics_point_facility_identity",
        ),
        sa.CheckConstraint(
            "lifecycle_status IN ('DRAFT','ACTIVE','DEPRECATED')",
            name="ck_global_logistics_point_lifecycle",
        ),
        sa.CheckConstraint(
            "verification_status IN ('UNVERIFIED','REVIEWED','VERIFIED')",
            name="ck_global_logistics_point_verification",
        ),
        sa.CheckConstraint(
            "border_side IS NULL OR border_side IN ('ENTRY','EXIT','BIDIRECTIONAL','NOT_APPLICABLE')",
            name="ck_global_logistics_point_border_side",
        ),
        sa.CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL) OR "
            "(latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180)",
            name="ck_global_logistics_point_coordinates",
        ),
        sa.CheckConstraint("version >= 1", name="ck_global_logistics_point_version"),
    )
    op.create_index(
        "ix_global_logistics_point_catalog",
        "global_logistics_point",
        [
            "lifecycle_status",
            "verification_status",
            "country_id",
            "logistics_point_type_id",
        ],
    )
    op.create_index(
        "ix_global_logistics_point_name",
        "global_logistics_point",
        ["normalized_name"],
    )
    op.create_index(
        "ix_global_logistics_point_geography",
        "global_logistics_point",
        ["geography_key"],
    )

    op.create_table(
        "global_logistics_point_alias",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column(
            "global_logistics_point_id",
            BIGINT,
            sa.ForeignKey("global_logistics_point.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alias", sa.String(160), nullable=False),
        sa.Column("normalized_alias", sa.String(200), nullable=False),
        sa.Column("language_code", sa.String(16)),
        sa.UniqueConstraint(
            "global_logistics_point_id",
            "normalized_alias",
            name="uq_global_logistics_point_alias",
        ),
    )
    op.create_index(
        "ix_global_logistics_point_alias_search",
        "global_logistics_point_alias",
        ["normalized_alias"],
    )

    op.create_table(
        "global_logistics_point_mode",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column(
            "global_logistics_point_id",
            BIGINT,
            sa.ForeignKey("global_logistics_point.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("mode_code", sa.String(16), nullable=False),
        sa.UniqueConstraint(
            "global_logistics_point_id",
            "mode_code",
            name="uq_global_logistics_point_mode",
        ),
        sa.CheckConstraint(
            "mode_code IN ('ROAD','RAIL','SEA','AIR','MULTIMODAL')",
            name="ck_global_logistics_point_mode_code",
        ),
    )
    op.create_index(
        "ix_global_logistics_point_mode_code",
        "global_logistics_point_mode",
        ["mode_code"],
    )

    op.create_table(
        "global_logistics_point_external_code",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column(
            "global_logistics_point_id",
            BIGINT,
            sa.ForeignKey("global_logistics_point.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scheme", sa.String(64), nullable=False),
        sa.Column("value", sa.String(160), nullable=False),
        sa.Column("normalized_value", sa.String(160), nullable=False),
        sa.Column("source_reference", sa.String(500)),
        sa.UniqueConstraint(
            "global_logistics_point_id",
            "scheme",
            "normalized_value",
            name="uq_global_logistics_point_external_code",
        ),
    )
    op.create_index(
        "ix_global_logistics_point_external_code_search",
        "global_logistics_point_external_code",
        ["scheme", "normalized_value"],
    )

    op.create_table(
        "global_logistics_point_corridor_tag",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column(
            "global_logistics_point_id",
            BIGINT,
            sa.ForeignKey("global_logistics_point.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tag_code", sa.String(64), nullable=False),
        sa.UniqueConstraint(
            "global_logistics_point_id",
            "tag_code",
            name="uq_global_logistics_point_corridor_tag",
        ),
    )
    op.create_index(
        "ix_global_logistics_point_corridor_tag_code",
        "global_logistics_point_corridor_tag",
        ["tag_code"],
    )

    op.create_table(
        "global_logistics_point_source",
        sa.Column("id", BIGINT, primary_key=True),
        sa.Column(
            "global_logistics_point_id",
            BIGINT,
            sa.ForeignKey("global_logistics_point.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_organization", sa.String(160), nullable=False),
        sa.Column("source_reference", sa.String(500), nullable=False),
        sa.Column(
            "source_version", sa.String(100), nullable=False, server_default="unspecified"
        ),
        sa.Column("retrieved_at", sa.DateTime(timezone=True)),
        sa.Column(
            "reviewed_by",
            BIGINT,
            sa.ForeignKey("expert_user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "global_logistics_point_id",
            "source_organization",
            "source_reference",
            "source_version",
            name="uq_global_logistics_point_source",
        ),
    )


def downgrade():
    op.drop_table("global_logistics_point_source")
    op.drop_index(
        "ix_global_logistics_point_corridor_tag_code",
        table_name="global_logistics_point_corridor_tag",
    )
    op.drop_table("global_logistics_point_corridor_tag")
    op.drop_index(
        "ix_global_logistics_point_external_code_search",
        table_name="global_logistics_point_external_code",
    )
    op.drop_table("global_logistics_point_external_code")
    op.drop_index(
        "ix_global_logistics_point_mode_code",
        table_name="global_logistics_point_mode",
    )
    op.drop_table("global_logistics_point_mode")
    op.drop_index(
        "ix_global_logistics_point_alias_search",
        table_name="global_logistics_point_alias",
    )
    op.drop_table("global_logistics_point_alias")
    op.drop_index(
        "ix_global_logistics_point_geography", table_name="global_logistics_point"
    )
    op.drop_index(
        "ix_global_logistics_point_name", table_name="global_logistics_point"
    )
    op.drop_index(
        "ix_global_logistics_point_catalog", table_name="global_logistics_point"
    )
    op.drop_table("global_logistics_point")
