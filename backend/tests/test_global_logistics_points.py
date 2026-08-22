"""ADR-041 Phase 1 schema and platform read API contract."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from backend import create_app
from backend.auth import auth_manager
from backend.extensions import db
from backend.global_logistics_point_models import (
    GlobalLogisticsPoint,
    GlobalLogisticsPointAlias,
    GlobalLogisticsPointCorridorTag,
    GlobalLogisticsPointExternalCode,
    GlobalLogisticsPointMode,
    GlobalLogisticsPointSource,
)
from backend.logistics_network_models import LogisticsPoint, LogisticsPointType
from backend.models import Country, ExpertUser, TrackingLocationReference
from backend.operational_models import OperationalMembership, OperationalOrganization


@pytest.fixture()
def global_catalog_app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "global-catalog-test",
        }
    )
    with app.app_context():
        db.create_all()
        platform = ExpertUser(
            username="global-platform",
            password_hash="x",
            full_name="Platform",
            role="admin",
            authority="PLATFORM_ADMIN",
            is_active=True,
        )
        organization_admin = ExpertUser(
            username="global-org-admin",
            password_hash="x",
            full_name="Organization Admin",
            role="admin",
            authority="ORGANIZATION_ADMIN",
            is_active=True,
        )
        expert = ExpertUser(
            username="global-expert",
            password_hash="x",
            full_name="Expert",
            role="expert",
            authority="EXPERT",
            is_active=True,
        )
        organization = OperationalOrganization(name="Global Catalog Tenant")
        china = Country(code="CN", name_en="China", name_fa="چین")
        iran = Country(code="IR", name_en="Iran", name_fa="ایران")
        port_type = LogisticsPointType(
            immutable_code="PORT",
            fa_name="بندر",
            en_name="Port",
            created_by=1,
            updated_by=1,
        )
        border_type = LogisticsPointType(
            immutable_code="BORDER_CROSSING",
            fa_name="مرز",
            en_name="Border crossing",
            created_by=1,
            updated_by=1,
        )
        db.session.add_all(
            [
                platform,
                organization_admin,
                expert,
                organization,
                china,
                iran,
            ]
        )
        db.session.flush()
        port_type.created_by = port_type.updated_by = platform.id
        border_type.created_by = border_type.updated_by = platform.id
        db.session.add_all([port_type, border_type])
        db.session.flush()
        db.session.add_all(
            [
                OperationalMembership(
                    organization_id=organization.id,
                    user_id=organization_admin.id,
                    permissions=["logistics_point.read", "logistics_point.manage"],
                ),
                OperationalMembership(
                    organization_id=organization.id,
                    user_id=expert.id,
                    permissions=["logistics_point.read"],
                ),
            ]
        )

        def point(code, fa_name, en_name, country, point_type, *, status="ACTIVE"):
            row = GlobalLogisticsPoint(
                immutable_code=code,
                logistics_point_type_id=point_type.id,
                fa_name=fa_name,
                en_name=en_name,
                normalized_name=en_name.lower(),
                country_id=country.id,
                city_name=en_name.split()[0],
                geography_key=f"{country.code}:{code}",
                facility_identity_key=code,
                lifecycle_status=status,
                verification_status="VERIFIED",
                timezone_name="Asia/Shanghai" if country.code == "CN" else "Asia/Tehran",
                created_by=platform.id,
                updated_by=platform.id,
            )
            row.aliases.append(
                GlobalLogisticsPointAlias(
                    alias=f"{en_name} Alias",
                    normalized_alias=f"{en_name.lower()} alias",
                    language_code="en",
                )
            )
            row.modes.append(GlobalLogisticsPointMode(mode_code="SEA" if point_type == port_type else "ROAD"))
            row.corridor_tags.append(
                GlobalLogisticsPointCorridorTag(tag_code="CHINA_IRAN_V1")
            )
            row.external_codes.append(
                GlobalLogisticsPointExternalCode(
                    scheme="TEST", value=code, normalized_value=code
                )
            )
            row.sources.append(
                GlobalLogisticsPointSource(
                    source_organization="Test Authority",
                    source_reference=f"test:{code}",
                    source_version="1",
                    reviewed_by=platform.id,
                )
            )
            db.session.add(row)
            return row

        ningbo = point("CN-NINGBO-PORT", "بندر نینگبو", "Ningbo Port", china, port_type)
        sarakhs = point("IR-SARAKHS-BORDER", "مرز سرخس", "Sarakhs Border", iran, border_type)
        deprecated = point(
            "CN-OLD-PORT", "بندر قدیمی", "Old Port", china, port_type, status="DEPRECATED"
        )
        db.session.commit()
        yield app, {
            "platform": {"Authorization": f"Bearer {auth_manager.generate_tokens(platform.id)['access_token']}"},
            "organization_admin": {"Authorization": f"Bearer {auth_manager.generate_tokens(organization_admin.id)['access_token']}"},
            "expert": {"Authorization": f"Bearer {auth_manager.generate_tokens(expert.id)['access_token']}"},
            "platform_id": platform.id,
            "country_id": china.id,
            "type_id": port_type.id,
            "ningbo": ningbo.public_id,
            "sarakhs": sarakhs.public_id,
            "deprecated": deprecated.public_id,
        }
        db.session.remove()
        db.drop_all()


def test_schema_identity_constraints_and_existing_domains_are_untouched(global_catalog_app):
    app, ctx = global_catalog_app
    with app.app_context():
        assert "organization_id" not in GlobalLogisticsPoint.__table__.columns
        assert LogisticsPoint.__table__.columns.organization_id.nullable is False
        assert TrackingLocationReference.__table__.name == "tracking_location_reference"
        assert GlobalLogisticsPoint.__table__.columns.logistics_point_type_id.nullable is False
        assert GlobalLogisticsPoint.__table__.columns.country_id.nullable is False

        duplicate = GlobalLogisticsPoint(
            public_id=ctx["ningbo"],
            immutable_code="OTHER-CODE",
            logistics_point_type_id=ctx["type_id"],
            fa_name="تکراری",
            en_name="Duplicate",
            normalized_name="duplicate",
            country_id=ctx["country_id"],
            geography_key="CN:DUP",
            facility_identity_key="DUP",
            lifecycle_status="DRAFT",
            verification_status="UNVERIFIED",
            created_by=ctx["platform_id"],
            updated_by=ctx["platform_id"],
        )
        db.session.add(duplicate)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        duplicate_code = GlobalLogisticsPoint(
            public_id=str(uuid4()),
            immutable_code="CN-NINGBO-PORT",
            logistics_point_type_id=ctx["type_id"],
            fa_name="تکراری",
            en_name="Duplicate code",
            normalized_name="duplicate code",
            country_id=ctx["country_id"],
            geography_key="CN:DUP2",
            facility_identity_key="DUP2",
            lifecycle_status="DRAFT",
            verification_status="UNVERIFIED",
            created_by=ctx["platform_id"],
            updated_by=ctx["platform_id"],
        )
        db.session.add(duplicate_code)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        point = db.session.scalar(
            db.select(GlobalLogisticsPoint).where(
                GlobalLogisticsPoint.public_id == ctx["ningbo"]
            )
        )
        point.immutable_code = "MUTATED"
        with pytest.raises(ValueError, match="immutable_code"):
            db.session.flush()
        db.session.rollback()

        point = db.session.scalar(
            db.select(GlobalLogisticsPoint).where(
                GlobalLogisticsPoint.public_id == ctx["ningbo"]
            )
        )
        point.version = 0
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


def test_platform_read_requires_platform_authority_not_membership(global_catalog_app):
    app, ctx = global_catalog_app
    endpoint = "/api/platform/global-logistics-points"
    with app.test_client() as client:
        assert client.get(endpoint, headers=ctx["platform"]).status_code == 200
        assert client.get(endpoint, headers=ctx["organization_admin"]).status_code == 403
        assert client.get(endpoint, headers=ctx["expert"]).status_code == 403
        assert client.get(endpoint).status_code == 401
        assert client.post(endpoint, headers=ctx["platform"], json={}).status_code == 405
        assert client.patch(f"{endpoint}/{ctx['ningbo']}", headers=ctx["platform"], json={}).status_code == 405


def test_list_filters_pagination_order_and_safe_projection(global_catalog_app):
    app, ctx = global_catalog_app
    endpoint = "/api/platform/global-logistics-points"
    with app.test_client() as client:
        response = client.get(endpoint, headers=ctx["platform"])
        assert response.status_code == 200
        payload = response.get_json()
        assert [item["immutable_code"] for item in payload["items"]] == [
            "CN-NINGBO-PORT",
            "IR-SARAKHS-BORDER",
        ]
        assert payload["per_page"] == 20 and payload["total"] == 2
        assert client.get(f"{endpoint}?q=Ningbo Port Alias", headers=ctx["platform"]).get_json()["total"] == 1
        assert client.get(f"{endpoint}?country=CN", headers=ctx["platform"]).get_json()["total"] == 1
        assert client.get(f"{endpoint}?type=PORT", headers=ctx["platform"]).get_json()["total"] == 1
        assert client.get(f"{endpoint}?mode=SEA", headers=ctx["platform"]).get_json()["total"] == 1
        assert client.get(f"{endpoint}?corridor=CHINA_IRAN_V1", headers=ctx["platform"]).get_json()["total"] == 2
        assert client.get(f"{endpoint}?status=DEPRECATED", headers=ctx["platform"]).get_json()["items"][0]["public_id"] == ctx["deprecated"]
        capped = client.get(f"{endpoint}?status=ALL&per_page=999", headers=ctx["platform"]).get_json()
        assert capped["per_page"] == 100 and capped["total"] == 3
        assert client.get(f"{endpoint}?q={'x' * 161}", headers=ctx["platform"]).status_code == 400

        item = payload["items"][0]
        forbidden = {"id", "organization_id", "created_by", "updated_by"}
        assert forbidden.isdisjoint(item)
        assert item["supported_modes"] == ["SEA"]
        assert item["external_codes"] == [{"scheme": "TEST", "value": "CN-NINGBO-PORT"}]


def test_detail_uses_only_opaque_identity_and_not_found_is_safe(global_catalog_app):
    app, ctx = global_catalog_app
    endpoint = "/api/platform/global-logistics-points"
    with app.test_client() as client:
        detail = client.get(f"{endpoint}/{ctx['ningbo']}", headers=ctx["platform"])
        assert detail.status_code == 200
        assert detail.get_json()["item"]["public_id"] == ctx["ningbo"]
        assert client.get(f"{endpoint}/{uuid4()}", headers=ctx["platform"]).status_code == 404
        assert client.get(f"{endpoint}/1", headers=ctx["platform"]).status_code == 404
        assert client.get(f"{endpoint}/not-a-uuid", headers=ctx["platform"]).status_code == 404
