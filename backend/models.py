"""Database models for the shipment request service."""
from datetime import datetime

from backend.extensions import db


class Province(db.Model):
    """Represents a province."""

    __tablename__ = "province"

    id = db.Column(db.BigInteger, primary_key=True)
    code = db.Column(db.String(10), nullable=True)
    name_fa = db.Column(db.Text, nullable=False)

    counties = db.relationship("County", back_populates="province", lazy=True)
    cities = db.relationship("City", back_populates="province", lazy=True)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Province id={self.id} name_fa={self.name_fa!r}>"


class County(db.Model):
    """Represents a county within a province."""

    __tablename__ = "county"

    id = db.Column(db.BigInteger, primary_key=True)
    province_id = db.Column(db.BigInteger, db.ForeignKey("province.id"), nullable=False)
    name_fa = db.Column(db.Text, nullable=False)

    province = db.relationship("Province", back_populates="counties")
    cities = db.relationship("City", back_populates="county", lazy=True)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<County id={self.id} name_fa={self.name_fa!r}>"


class City(db.Model):
    """Represents a city within a county."""

    __tablename__ = "city"

    id = db.Column(db.BigInteger, primary_key=True)
    county_id = db.Column(db.BigInteger, db.ForeignKey("county.id"), nullable=False)
    province_id = db.Column(db.BigInteger, db.ForeignKey("province.id"), nullable=False)
    name_fa = db.Column(db.Text, nullable=False)

    county = db.relationship("County", back_populates="cities")
    province = db.relationship("Province", back_populates="cities")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<City id={self.id} name_fa={self.name_fa!r}>"


class ShipmentRequest(db.Model):
    """Represents a shipment request submitted by a user."""

    __tablename__ = "shipment_request"

    id = db.Column(db.BigInteger, primary_key=True)
    origin_province_id = db.Column(
        db.BigInteger, db.ForeignKey("province.id"), nullable=False
    )
    origin_county_id = db.Column(
        db.BigInteger, db.ForeignKey("county.id"), nullable=False
    )
    origin_city_id = db.Column(db.BigInteger, db.ForeignKey("city.id"), nullable=False)
    dest_province_id = db.Column(db.BigInteger, db.ForeignKey("province.id"), nullable=False)
    dest_county_id = db.Column(db.BigInteger, db.ForeignKey("county.id"), nullable=False)
    dest_city_id = db.Column(db.BigInteger, db.ForeignKey("city.id"), nullable=False)
    contact_phone = db.Column(db.String(32), nullable=False)
    transport_method = db.Column(db.String(32), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ready_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status_request_status = db.Column(db.String(32), nullable=False, default="new")
    request_user_id = db.Column(db.BigInteger, nullable=True)

    logs = db.relationship("ShipmentRequestLog", backref="shipment_request", lazy=True)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<ShipmentRequest id={self.id}>"


class ShipmentRequestLog(db.Model):
    """Log entries for shipment request lifecycle events."""

    __tablename__ = "shipment_request_log"

    id = db.Column(db.BigInteger, primary_key=True)
    shipment_request_id = db.Column(
        db.BigInteger, db.ForeignKey("shipment_request.id"), nullable=False
    )
    created_at = db.Column(db.DateTime, nullable=False)
    note = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.Text, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            "<ShipmentRequestLog "
            f"id={self.id} shipment_request_id={self.shipment_request_id}>"
        )


__all__ = [
    "Province",
    "County",
    "City",
    "ShipmentRequest",
    "ShipmentRequestLog",
]
