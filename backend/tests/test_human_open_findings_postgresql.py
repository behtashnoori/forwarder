"""Owned PG18 proof: canonical identity/search and Expert → Admin location lifecycle."""
import os
from copy import deepcopy

from alembic import command
import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url

from backend import create_app
from backend.extensions import db
from backend.migration_runtime import alembic_config
from backend.logistics_network_models import LogisticsPointType
from backend.models import Country, City, Province, ExpertUser
from backend.operational_models import OperationalMembership, OperationalShipment, RouteLeg
from backend.services import logistics_network_service as geo, operational_service as ops
from backend.services.location_resolver import resolve_location
from backend.services.operational_service import OperationalError
from backend.tests.test_phase3_transport_execution_postgresql import _seed_runtime
from scripts.uat.canonical_geography_fixture import ensure_canonical_geography

URL = os.environ.get("HUMAN_OPEN_FINDINGS_POSTGRES_URL", "")
pytestmark = pytest.mark.skipif(not URL, reason="requires owned HUMAN_OPEN_FINDINGS_POSTGRES_URL")


def test_canonical_search_parentage_pagination_and_location_review_preserve_usage():
    parsed = make_url(URL)
    assert parsed.get_backend_name() == "postgresql" and parsed.host == "127.0.0.1"
    assert parsed.database.startswith("forwarder_human_open_findings_")
    engine = sa.create_engine(URL)
    with engine.connect() as connection:
        assert 180000 <= int(connection.execute(sa.text("SHOW server_version_num")).scalar_one()) < 190000
    command.upgrade(alembic_config(URL), "20261016_active_route_basis")
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": URL, "SECRET_KEY": "owned-hw"}, skip_startup=True)
    with app.app_context():
        ctx = _seed_runtime(app)
        ensure_canonical_geography()
        member = OperationalMembership.query.filter_by(user_id=ctx["owner"]).one()
        member.permissions = [*member.permissions, "operational_shipment.create_direct"]
        shipment = OperationalShipment.query.filter_by(public_id=ctx["shipment"]).one()
        admin = ExpertUser(username="hw-admin", full_name="HW Admin", password_hash="unused", role="admin", authority="ORGANIZATION_ADMIN", is_active=True)
        db.session.add(admin); db.session.flush()
        db.session.add(LogisticsPointType(
            immutable_code="HW_SYNTHETIC",
            fa_name="نوع نقطه آزمایشی",
            en_name="Synthetic point type",
            display_order=1,
            created_by=admin.id,
            updated_by=admin.id,
        ))
        db.session.add(OperationalMembership(user_id=admin.id, organization_id=shipment.organization_id, permissions=["logistics_point.read", "logistics_point.manage"]))
        db.session.commit()
        owner, reviewer = {"id": ctx["owner"]}, {"id": admin.id, "role": "admin"}
        countries = geo.canonical_countries({})["items"]
        assert len(countries) == Country.query.filter_by(is_active=True).count() == 249
        assert len([row for row in countries if row["geography_supported"]]) == 14
        assert geo.canonical_countries({"q": "Iran"})["items"][0]["code"] == "IR"
        assert geo.canonical_admin1({"country_code": "DE"})["items"] == []
        regions = geo.canonical_admin1({"country_code": "IR"})["items"]
        assert len(regions) == 31
        assert next(row for row in regions if row["geoname_id"] == 131222)["name_fa"] == "هرمزگان"
        assert geo.canonical_admin1({"country_code": "IR", "q": "اصفهان"})["items"][0]["geoname_id"] == 418862
        for region_id, city_id, fa, en in ((110791,112931,"تهران","Tehran"),(418862,418863,"اصفهان","Isfahan"),(131222,141681,"بندرعباس","Bandar Abbas")):
            by_fa = geo.canonical_cities({"admin1_geoname_id": region_id, "q": fa})
            by_en = geo.canonical_cities({"admin1_geoname_id": region_id, "q": en})
            row = next(row for row in by_fa["items"] if row["geoname_id"] == city_id)
            assert row in by_en["items"] and row["name_fa"] == fa
            assert len({item["geoname_id"] for item in by_fa["items"]}) == len(by_fa["items"])
            resolved = resolve_location({"source_type":"city", "source_id":row["source_id"]})
            assert resolved.display_label == fa
            city = db.session.get(City, row["source_id"])
            assert db.session.get(Province, city.province_id).geoname_id == region_id
        assert geo.canonical_cities({"admin1_geoname_id":418862,"q":"أصفهان"}) == geo.canonical_cities({"admin1_geoname_id":418862,"q":"اصفهان"})
        largest = db.session.execute(sa.select(Province.geoname_id,sa.func.count(City.id)).join(City).where(Province.dataset_id==geo.GEONAMES_DATASET_ID).group_by(Province.id).order_by(sa.func.count(City.id).desc())).first()
        all_ids=[]; offset=0
        while True:
            page=geo.canonical_cities({"admin1_geoname_id":largest[0],"offset":offset})
            all_ids.extend(row["geoname_id"] for row in page["items"])
            if not page["has_more"]: break
            offset += 200
        assert len(all_ids) == len(set(all_ids)) == largest[1] and offset > 0
        point = geo.create_expert_point({"name":"انبار آزمون اصفهان","city_geoname_id":418863},owner)
        db.session.commit()
        assert point.governance_state == "PENDING_REVIEW" and point.is_active
        ref={"source_type":"logistics_point","source_id":point.public_id}
        endpoint=ops._endpoint(ref,shipment.organization_id)
        leg=db.session.get(RouteLeg,ctx["leg"])
        leg.origin_snapshot=ops._endpoint_snapshot(endpoint)
        db.session.commit(); before=deepcopy(leg.origin_snapshot)
        listed=geo.list_points({"city_geoname_id":418863},owner)["items"]
        assert next(row for row in listed if row["public_id"]==point.public_id)["city"]["name_fa"]=="اصفهان"
        assert geo.list_points({},reviewer,admin=True)["items"][0]["public_id"]==point.public_id
        point=geo.scoped_point(point.public_id,reviewer,"logistics_point.manage")
        point_type = geo.list_types({}, admin=True)["items"][0]
        geo.update_point(point,{"version":point.version,"short_address":"نشانی تکمیل‌شده",
            "point_type_public_id":point_type["public_id"],"description":"کارخانه عملیاتی",
            "latitude":"32.6546","longitude":"51.6680"},reviewer)
        geo.review_point(point,"approve",{"version":point.version},reviewer); db.session.commit()
        completed=geo.list_points({},owner)["items"][0]
        assert completed["governance_state"]=="APPROVED"
        assert completed["point_type"]["public_id"]==point_type["public_id"]
        assert completed["description"]=="کارخانه عملیاتی"
        assert completed["latitude"]=="32.6546000" and completed["longitude"]=="51.6680000"
        assert ops._endpoint(ref,shipment.organization_id).logistics_point.id==point.id
        with pytest.raises(OperationalError): geo.scoped_point(point.public_id,{"id":ctx["outsider"]},"execution_unit.update")
        db.session.rollback()
        geo.review_point(point,"deactivate",{"version":point.version},reviewer); db.session.commit()
        assert not geo.list_points({},owner)["items"]
        with pytest.raises(OperationalError) as denied: ops._endpoint(ref,shipment.organization_id)
        assert denied.value.code=="LOCATION_MAPPING_REQUIRED"
        assert db.session.get(RouteLeg,ctx["leg"]).origin_snapshot == before
        assert db.session.get(City, next(row for row in geo.canonical_cities({"admin1_geoname_id":418862,"q":"اصفهان"})["items"] if row["geoname_id"]==418863)["source_id"]).name_fa == "أصفهان"
    engine.dispose()
