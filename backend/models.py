"""Database models for the shipment request service."""
from datetime import datetime

from backend.extensions import db


class Province(db.Model):
    """Represents a province."""

    __tablename__ = "province"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)

    counties = db.relationship("County", backref="province", lazy=True)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Province id={self.id} name={self.name!r}>"


class County(db.Model):
    """Represents a county within a province."""

    __tablename__ = "county"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    province_id = db.Column(db.Integer, db.ForeignKey("province.id"), nullable=False)

    cities = db.relationship("City", backref="county", lazy=True)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<County id={self.id} name={self.name!r}>"


class City(db.Model):
    """Represents a city within a county."""

    __tablename__ = "city"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    county_id = db.Column(db.Integer, db.ForeignKey("county.id"), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<City id={self.id} name={self.name!r}>"


class ShipmentRequest(db.Model):
    """Represents a shipment request submitted by a user."""

    __tablename__ = "shipment_request"

    id = db.Column(db.Integer, primary_key=True)
    origin_province_id = db.Column(
        db.Integer, db.ForeignKey("province.id"), nullable=False
    )
    origin_county_id = db.Column(db.Integer, db.ForeignKey("county.id"), nullable=False)
    origin_city_id = db.Column(db.Integer, db.ForeignKey("city.id"), nullable=False)
    dest_province_id = db.Column(db.Integer, db.ForeignKey("province.id"), nullable=False)
    dest_county_id = db.Column(db.Integer, db.ForeignKey("county.id"), nullable=False)
    dest_city_id = db.Column(db.Integer, db.ForeignKey("city.id"), nullable=False)
    contact_phone = db.Column(db.String(32), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ready_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status_request_status = db.Column(db.String(32), nullable=False, default="new")
    request_user_id = db.Column(db.Integer, nullable=True)

    logs = db.relationship("ShipmentRequestLog", backref="shipment_request", lazy=True)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<ShipmentRequest id={self.id}>"


class ShipmentRequestLog(db.Model):
    """Log entries for shipment request lifecycle events."""

    __tablename__ = "shipment_request_log"

    id = db.Column(db.Integer, primary_key=True)
    shipment_request_id = db.Column(
        db.Integer, db.ForeignKey("shipment_request.id"), nullable=False
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
