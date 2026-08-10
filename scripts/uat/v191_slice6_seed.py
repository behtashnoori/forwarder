"""Provision deterministic Slice 6 personas after the repository-native UAT seed."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import bcrypt

from backend import create_app
from backend.extensions import db
from backend.models import City, Country, County, Customer, CustomsOffice, ExpertQuote, ExpertUser, InternationalCity, IranPort, PortLocation, Province, ShipmentRequest
from backend.operational_cli import PHASE1B_ALL_PERMISSIONS, PHASE1B_NOW, seed_phase1b_uat
from backend.operational_models import OperationalMembership, OperationalOrganization


def main() -> None:
    app = create_app(skip_startup=True)
    with app.app_context():
        password = os.environ["FORWARDER_UAT_PASSWORD"]
        seed_phase1b_uat(app, password)
        organization = OperationalOrganization.query.filter_by(name="[PHASE1B-UAT] Organization A").one()
        base_read = ["operational_shipment.read", "work_item.read", "route_plan.read", "checkpoint.read", "route_exception.read", "operational_execution.read", "document_readiness.read"]
        personas = {
            "direct_only": [*base_read, "operational_shipment.create_direct"],
            "quote_only": [*base_read, "operational_shipment.create_from_quote"],
            "legacy_quote": [*base_read, "operational_shipment.create"],
            "both": [*base_read, "operational_shipment.create_direct", "operational_shipment.create_from_quote"],
        }
        for suffix, permissions in personas.items():
            user = ExpertUser(username=f"phase1b_uat_{suffix}", password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(), full_name=f"[SLICE6-UAT] {suffix}", role="expert", is_active=True)
            db.session.add(user)
            db.session.flush()
            db.session.add(OperationalMembership(organization_id=organization.id, user_id=user.id, permissions=permissions))
        admin = ExpertUser.query.filter_by(username="phase1b_uat_admin").one()
        admin.role = "admin"
        membership = OperationalMembership.query.filter_by(user_id=admin.id).one()
        economics_permissions = {
            "economics.revenue.view", "economics.cost.view",
            "economics.estimate.create", "economics.commitment.create",
            "economics.actual.create", "economics.observation.correct",
            "economics.fx.approve",
        }
        membership.permissions = sorted(set(PHASE1B_ALL_PERMISSIONS) | economics_permissions | {"operational_shipment.create_direct", "operational_shipment.create_from_quote"})
        for code, en, fa, cities in (
            ("IR", "Iran", "ایران", ()),
            ("CHN", "China", "چین", (("Shanghai", "شانگهای", "port"),)),
            ("TUR", "Turkey", "ترکیه", (("Istanbul", "استانبول", "city"),)),
        ):
            country = Country.query.filter_by(code=code).one_or_none()
            if country is None:
                country = Country(code=code, name_en=en, name_fa=fa, is_active=True)
                db.session.add(country)
                db.session.flush()
            for city_en, city_fa, city_type in cities:
                if InternationalCity.query.filter_by(country_id=country.id, name_en=city_en).one_or_none() is None:
                    db.session.add(InternationalCity(country_id=country.id, name_en=city_en, name_fa=city_fa, city_type=city_type, is_active=True))
        iran = Country.query.filter_by(code="IR").one()
        provinces = Province.query.filter_by(is_active=True).order_by(Province.id).limit(2).all()
        for province in provinces:
            province.country_id = iran.id
        db.session.flush()
        counties = []
        for index, province in enumerate(provinces, 1):
            county = County(code=f"UAT{index}", name_fa=f"شهرستان پذیرش {index}", province_id=province.id, is_active=True)
            db.session.add(county)
            counties.append(county)
        db.session.flush()
        cities = []
        for index, (province, county) in enumerate(zip(provinces, counties), 1):
            city = City(code=f"UAT{index}", name_fa="مقصد تکراری", county_id=county.id, province_id=province.id, is_active=True)
            db.session.add(city)
            cities.append(city)
        db.session.flush()
        port = IranPort(code="UATP", name_en="UAT Port", name_fa="بندر پذیرش", port_type="sea", province_id=provinces[1].id, country_id=iran.id, is_active=True)
        db.session.add(port)
        db.session.flush()
        db.session.add(PortLocation(port_id=port.id, country_id=iran.id, province_id=provinces[1].id, location_status="confirmed"))
        db.session.add(CustomsOffice(code="UATC", name_en="UAT Customs", name_fa="مقصد تکراری", customs_type="road_border", country_id=iran.id, province_id=provinces[0].id, county_id=counties[0].id, city_id=cities[0].id, is_active=True))
        for sequence in range(1, 9):
            phone = f"090000006{sequence:02d}"
            customer = Customer(first_name="Governed", last_name=f"Slice 6 Customer {sequence}", phone=phone, status="active")
            db.session.add(customer)
            db.session.flush()
            request = ShipmentRequest(contact_phone=phone, customer_first_name="Governed", customer_last_name=f"Slice 6 Customer {sequence}", status="waiting_for_customer", status_request_status="new", assigned_to=admin.id, customer_id=customer.id)
            db.session.add(request)
            db.session.flush()
            db.session.add(ExpertQuote(shipment_request_id=request.id, amount=1910 + sequence, currency="USD", created_by_expert_id=admin.id, created_at=PHASE1B_NOW, customer_response="accepted", responded_at=PHASE1B_NOW, operational_organization_id=organization.id))
        db.session.commit()


if __name__ == "__main__":
    main()
