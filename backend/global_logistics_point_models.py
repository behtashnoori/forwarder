"""Platform-owned Global Logistics Point foundation accepted by ADR-041."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import event, inspect

from backend.extensions import db
from backend.operational_models import BIGINT, utcnow


GLOBAL_POINT_LIFECYCLES = frozenset({"DRAFT", "ACTIVE", "DEPRECATED"})
GLOBAL_POINT_VERIFICATION_STATES = frozenset(
    {"UNVERIFIED", "REVIEWED", "VERIFIED"}
)
GLOBAL_POINT_MODES = frozenset({"ROAD", "RAIL", "SEA", "AIR", "MULTIMODAL"})
GLOBAL_POINT_BORDER_SIDES = frozenset(
    {"ENTRY", "EXIT", "BIDIRECTIONAL", "NOT_APPLICABLE"}
)


class GlobalLogisticsPoint(db.Model):
    """Canonical platform identity for one reviewed real-world logistics place."""

    __tablename__ = "global_logistics_point"
    __table_args__ = (
        db.UniqueConstraint("public_id", name="uq_global_logistics_point_public_id"),
        db.UniqueConstraint(
            "immutable_code", name="uq_global_logistics_point_immutable_code"
        ),
        db.UniqueConstraint(
            "country_id",
            "logistics_point_type_id",
            "facility_identity_key",
            name="uq_global_logistics_point_facility_identity",
        ),
        db.CheckConstraint(
            "lifecycle_status IN ('DRAFT','ACTIVE','DEPRECATED')",
            name="ck_global_logistics_point_lifecycle",
        ),
        db.CheckConstraint(
            "verification_status IN ('UNVERIFIED','REVIEWED','VERIFIED')",
            name="ck_global_logistics_point_verification",
        ),
        db.CheckConstraint(
            "border_side IS NULL OR border_side IN ('ENTRY','EXIT','BIDIRECTIONAL','NOT_APPLICABLE')",
            name="ck_global_logistics_point_border_side",
        ),
        db.CheckConstraint(
            "(latitude IS NULL AND longitude IS NULL) OR "
            "(latitude BETWEEN -90 AND 90 AND longitude BETWEEN -180 AND 180)",
            name="ck_global_logistics_point_coordinates",
        ),
        db.CheckConstraint("version >= 1", name="ck_global_logistics_point_version"),
        db.Index(
            "ix_global_logistics_point_catalog",
            "lifecycle_status",
            "verification_status",
            "country_id",
            "logistics_point_type_id",
        ),
        db.Index("ix_global_logistics_point_name", "normalized_name"),
        db.Index("ix_global_logistics_point_geography", "geography_key"),
    )

    id = db.Column(BIGINT, primary_key=True)
    public_id = db.Column(
        db.String(36), nullable=False, default=lambda: str(uuid4())
    )
    immutable_code = db.Column(db.String(64), nullable=False)
    logistics_point_type_id = db.Column(
        BIGINT,
        db.ForeignKey("logistics_point_type.id", ondelete="RESTRICT"),
        nullable=False,
    )
    fa_name = db.Column(db.String(160), nullable=False)
    en_name = db.Column(db.String(160), nullable=False)
    normalized_name = db.Column(db.String(200), nullable=False)
    country_id = db.Column(
        BIGINT, db.ForeignKey("country.id", ondelete="RESTRICT"), nullable=False
    )
    province_id = db.Column(
        BIGINT, db.ForeignKey("province.id", ondelete="RESTRICT"), nullable=True
    )
    city_id = db.Column(
        BIGINT, db.ForeignKey("city.id", ondelete="RESTRICT"), nullable=True
    )
    international_city_id = db.Column(
        BIGINT,
        db.ForeignKey("international_city.id", ondelete="RESTRICT"),
        nullable=True,
    )
    region_name = db.Column(db.String(160), nullable=True)
    city_name = db.Column(db.String(160), nullable=True)
    geography_key = db.Column(db.String(240), nullable=False)
    facility_identity_key = db.Column(db.String(240), nullable=False)
    short_address = db.Column(db.String(500), nullable=True)
    latitude = db.Column(db.Numeric(9, 6), nullable=True)
    longitude = db.Column(db.Numeric(9, 6), nullable=True)
    timezone_name = db.Column(db.String(64), nullable=True)
    un_locode = db.Column(db.String(5), nullable=True)
    border_pair_key = db.Column(db.String(100), nullable=True)
    border_side = db.Column(db.String(16), nullable=True)
    lifecycle_status = db.Column(db.String(16), nullable=False, default="DRAFT")
    verification_status = db.Column(
        db.String(16), nullable=False, default="UNVERIFIED"
    )
    version = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )
    created_by = db.Column(
        BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False
    )
    updated_by = db.Column(
        BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False
    )

    point_type = db.relationship("LogisticsPointType")
    country = db.relationship("Country")
    province = db.relationship("Province")
    city = db.relationship("City")
    international_city = db.relationship("InternationalCity")
    aliases = db.relationship(
        "GlobalLogisticsPointAlias", cascade="all, delete-orphan", lazy="selectin"
    )
    modes = db.relationship(
        "GlobalLogisticsPointMode", cascade="all, delete-orphan", lazy="selectin"
    )
    external_codes = db.relationship(
        "GlobalLogisticsPointExternalCode",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    corridor_tags = db.relationship(
        "GlobalLogisticsPointCorridorTag",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    sources = db.relationship(
        "GlobalLogisticsPointSource", cascade="all, delete-orphan", lazy="selectin"
    )
    __mapper_args__ = {"version_id_col": version, "version_id_generator": False}


class GlobalLogisticsPointAlias(db.Model):
    __tablename__ = "global_logistics_point_alias"
    __table_args__ = (
        db.UniqueConstraint(
            "global_logistics_point_id",
            "normalized_alias",
            name="uq_global_logistics_point_alias",
        ),
        db.Index("ix_global_logistics_point_alias_search", "normalized_alias"),
    )
    id = db.Column(BIGINT, primary_key=True)
    global_logistics_point_id = db.Column(
        BIGINT,
        db.ForeignKey("global_logistics_point.id", ondelete="CASCADE"),
        nullable=False,
    )
    alias = db.Column(db.String(160), nullable=False)
    normalized_alias = db.Column(db.String(200), nullable=False)
    language_code = db.Column(db.String(16), nullable=True)


class GlobalLogisticsPointMode(db.Model):
    __tablename__ = "global_logistics_point_mode"
    __table_args__ = (
        db.UniqueConstraint(
            "global_logistics_point_id",
            "mode_code",
            name="uq_global_logistics_point_mode",
        ),
        db.CheckConstraint(
            "mode_code IN ('ROAD','RAIL','SEA','AIR','MULTIMODAL')",
            name="ck_global_logistics_point_mode_code",
        ),
        db.Index("ix_global_logistics_point_mode_code", "mode_code"),
    )
    id = db.Column(BIGINT, primary_key=True)
    global_logistics_point_id = db.Column(
        BIGINT,
        db.ForeignKey("global_logistics_point.id", ondelete="CASCADE"),
        nullable=False,
    )
    mode_code = db.Column(db.String(16), nullable=False)


class GlobalLogisticsPointExternalCode(db.Model):
    __tablename__ = "global_logistics_point_external_code"
    __table_args__ = (
        db.UniqueConstraint(
            "global_logistics_point_id",
            "scheme",
            "normalized_value",
            name="uq_global_logistics_point_external_code",
        ),
        db.Index(
            "ix_global_logistics_point_external_code_search",
            "scheme",
            "normalized_value",
        ),
    )
    id = db.Column(BIGINT, primary_key=True)
    global_logistics_point_id = db.Column(
        BIGINT,
        db.ForeignKey("global_logistics_point.id", ondelete="CASCADE"),
        nullable=False,
    )
    scheme = db.Column(db.String(64), nullable=False)
    value = db.Column(db.String(160), nullable=False)
    normalized_value = db.Column(db.String(160), nullable=False)
    source_reference = db.Column(db.String(500), nullable=True)


class GlobalLogisticsPointCorridorTag(db.Model):
    __tablename__ = "global_logistics_point_corridor_tag"
    __table_args__ = (
        db.UniqueConstraint(
            "global_logistics_point_id",
            "tag_code",
            name="uq_global_logistics_point_corridor_tag",
        ),
        db.Index("ix_global_logistics_point_corridor_tag_code", "tag_code"),
    )
    id = db.Column(BIGINT, primary_key=True)
    global_logistics_point_id = db.Column(
        BIGINT,
        db.ForeignKey("global_logistics_point.id", ondelete="CASCADE"),
        nullable=False,
    )
    tag_code = db.Column(db.String(64), nullable=False)


class GlobalLogisticsPointSource(db.Model):
    __tablename__ = "global_logistics_point_source"
    __table_args__ = (
        db.UniqueConstraint(
            "global_logistics_point_id",
            "source_organization",
            "source_reference",
            "source_version",
            name="uq_global_logistics_point_source",
        ),
    )
    id = db.Column(BIGINT, primary_key=True)
    global_logistics_point_id = db.Column(
        BIGINT,
        db.ForeignKey("global_logistics_point.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_organization = db.Column(db.String(160), nullable=False)
    source_reference = db.Column(db.String(500), nullable=False)
    source_version = db.Column(db.String(100), nullable=False, default="unspecified")
    retrieved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    reviewed_by = db.Column(
        BIGINT, db.ForeignKey("expert_user.id", ondelete="RESTRICT"), nullable=False
    )


@event.listens_for(GlobalLogisticsPoint, "before_update")
def _protect_global_point_identity(_mapper, _connection, target):
    state = inspect(target).attrs
    if state.immutable_code.history.has_changes():
        raise ValueError("immutable_code cannot be changed")
    if state.country_id.history.has_changes() or state.facility_identity_key.history.has_changes():
        raise ValueError("global logistics point facility identity cannot be changed")
