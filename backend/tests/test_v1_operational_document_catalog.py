from pathlib import Path

from backend.document_catalog_package import checksum_for_payload, load_package


PACKAGE_PATH = (
    Path(__file__).parents[1]
    / "reference_data"
    / "documents"
    / "document-catalog-v1-operational-generic-v1.0.0.json"
)


def test_v1_operational_document_package_is_valid_and_checksum_locked():
    package = load_package(PACKAGE_PATH)

    assert package.checksum == checksum_for_payload(package.payload)
    assert [item["name_fa"] for item in package.payload["definitions"]] == [
        "بارنامه",
        "فاکتور",
        "پکینگ لیست",
        "رسید تحویل",
    ]


def test_v1_operational_documents_are_generic_optional_capabilities():
    package = load_package(PACKAGE_PATH)

    for definition in package.payload["definitions"]:
        assert definition["organization_overridable"] is True
        assert definition["business_scopes"] == ["OPERATIONAL_SHIPMENT"]
        assert definition["transport_modes"] == ["MODE_INDEPENDENT"]
        assert definition["jurisdictions"] == [{"kind": "GLOBAL"}]
        assert definition["provenance"][0]["source_authority_code"] == "FORWARDER_PRODUCT_OWNER"
        assert "creates no statutory" in definition["provenance"][0]["notes"]
