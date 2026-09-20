"""Focused read-only contracts for Phase B3 existing transport projection."""
from copy import deepcopy

from backend.models import ShipmentRequest
from backend.services.request_transport_projection import (
    project_existing_request_transport,
)


def test_existing_request_transport_projection_is_exact_and_read_only():
    request = ShipmentRequest(
        contact_phone="09120000000",
        shipping_type="international",
        transport_method="road",
        domestic_transport_method="Rail Transport",
        international_transport_method="Sea Freight",
        transport_method_preference="customer_choice",
    )
    before = {
        "transport_method": request.transport_method,
        "domestic_transport_method": request.domestic_transport_method,
        "international_transport_method": request.international_transport_method,
        "transport_method_preference": request.transport_method_preference,
    }

    projection = project_existing_request_transport(request)

    assert projection == before
    assert {
        "transport_method": request.transport_method,
        "domestic_transport_method": request.domestic_transport_method,
        "international_transport_method": request.international_transport_method,
        "transport_method_preference": request.transport_method_preference,
    } == before
    assert deepcopy(projection) == projection
    assert "transport_intent" not in projection
    assert "classification" not in projection
    assert "multimodal" not in projection.values()


def test_missing_request_transport_remains_missing():
    request = ShipmentRequest(contact_phone="09120000000")
    assert project_existing_request_transport(request) == {
        "transport_method": None,
        "international_transport_method": None,
        "domestic_transport_method": None,
        "transport_method_preference": None,
    }
