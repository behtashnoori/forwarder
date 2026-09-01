from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.cargo_models import CargoCatalogItem
from backend.models import CargoType, UnitOfMeasure
from backend.services import cargo_service as svc


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("\u064a\u0649\u06cc", "\u06cc\u06cc\u06cc"),
        ("\u0643\u06a9", "\u06a9\u06a9"),
        ("\u06a9\u0627\u0644\u0627\u200c\u200c\u06cc", "\u06a9\u0627\u0644\u0627 \u06cc"),
        ("\u06f1\u06f2\u06f3 \u0664\u0665\u0666", "123 456"),
        ("  Alpha   BETA  ", "alpha beta"),
        ("\u06a9\u0627\u0644\u0627 ABC \u06f1\u0662", "\u06a9\u0627\u0644\u0627 abc 12"),
    ],
)
def test_alias_normalization_contract(source, expected):
    assert svc.normalize_text(source) == expected
    assert svc.normalize_text(source) == svc.normalize_text(source)


def test_alias_normalization_uses_nfc_without_false_merging():
    assert svc.normalize_text("A\u0301") == svc.normalize_text("\u00c1")
    assert svc.normalize_text("cargo-a") != svc.normalize_text("cargo a")
    assert svc.normalize_text("\u06a9\u0627\u0644\u0627") != svc.normalize_text("\u06a9\u0627\u0644\u0647")


def test_catalog_reference_validation_returns_precise_active_reference_errors(monkeypatch):
    monkeypatch.setattr(svc.db.session, "scalar", lambda _query: None)
    with pytest.raises(svc.CargoError, match="active cargo_type is required") as missing_type:
        svc.create_catalog({"id": 7}, {"immutable_code": "ITEM", "fa_name": "catalog"})
    assert missing_type.value.status == 422

    inactive = CargoType(public_id="inactive-type", immutable_code="INACTIVE", fa_name="type", en_name="Type", is_active=False)
    monkeypatch.setattr(svc.db.session, "scalar", lambda _query: inactive)
    with pytest.raises(svc.CargoError, match="active cargo_type is required"):
        svc.create_catalog({"id": 7}, {"immutable_code": "ITEM", "fa_name": "catalog", "cargo_type_public_id": "inactive-type"})


def _master_data():
    cargo_type = CargoType(
        public_id="ct-public", immutable_code="CARGO_TEST", fa_name="نوع", en_name="Type",
        description=None, display_order=1, is_active=True, version=1,
    )
    uom = UnitOfMeasure(
        public_id="uom-public", immutable_code="UOM_EA", fa_name="عدد", en_name="Each",
        description=None, display_order=1, is_active=True, version=1,
        symbol="ea", measurement_dimension="COUNT",
    )
    return cargo_type, uom


def _capture_create(monkeypatch, *, catalog=None, overrides=None):
    cargo_type, uom = _master_data()
    scalars = iter((cargo_type, uom))
    monkeypatch.setattr(svc.db.session, "scalar", lambda _query: next(scalars))
    monkeypatch.setattr(svc.db.session, "add", lambda _row: None)
    monkeypatch.setattr(svc.db.session, "commit", lambda: None)
    monkeypatch.setattr(svc.operational_service, "require_permission", lambda *_args: None)
    if catalog is not None:
        monkeypatch.setattr(svc, "scoped_catalog", lambda *_args, **_kwargs: catalog)
    payload = {
        "line_number": 1,
        "cargo_type_public_id": cargo_type.public_id,
        "uom_public_id": uom.public_id,
        "quantity": "12.5",
        "display_name": "Manual cargo",
        "part_number": "PN-MANUAL",
        "customer_item_code": "CUSTOMER-1",
        "hs_code": "1234",
        "brand": "Brand",
        "model": "Model",
        "description": "Creation evidence",
    }
    payload.update(overrides or {})
    row = svc.create_shipment_item(
        {"id": 7}, SimpleNamespace(id=99), payload
    )
    return row, cargo_type, uom


def test_manual_shipment_item_captures_supplied_creation_snapshot(monkeypatch):
    row, _, _ = _capture_create(monkeypatch)
    assert row.catalog_item is None
    assert row.display_name_snapshot == "Manual cargo"
    assert row.part_number_snapshot == "PN-MANUAL"
    assert row.customer_item_code_snapshot == "CUSTOMER-1"
    assert row.hs_code_snapshot == "1234"
    assert row.description_snapshot == "Creation evidence"
    assert row.quantity == svc.Decimal("12.5")


def test_catalog_linked_creation_captures_catalog_and_master_snapshots(monkeypatch):
    cargo_type, uom = _master_data()
    catalog = CargoCatalogItem(
        id=10, public_id="catalog-public", organization_id=1, immutable_code="ITEM-1",
        fa_name="کالای اصلی", en_name="Original", cargo_type=cargo_type,
        default_uom=uom, part_number="PN-OLD", customer_item_code="C-OLD",
        hs_code="HS-OLD", brand="B-OLD", model="M-OLD", description="D-OLD",
        search_text="", is_active=True, version=1, created_by=7, updated_by=7,
    )
    row, source_type, source_uom = _capture_create(
        monkeypatch,
        catalog=catalog,
        overrides={
            "catalog_item_public_id": catalog.public_id,
            "display_name": "ignored",
            "part_number": "",
            "customer_item_code": "",
            "hs_code": "",
            "brand": "",
            "model": "",
            "description": "",
        },
    )
    assert row.catalog_item is catalog
    assert row.display_name_snapshot == "کالای اصلی"
    assert row.part_number_snapshot == "PN-OLD"
    assert row.cargo_type_code_snapshot == "CARGO_TEST"
    assert row.uom_symbol_snapshot == "ea"
    catalog.fa_name, catalog.part_number = "نام جدید", "PN-NEW"
    source_type.fa_name, source_uom.symbol = "نوع جدید", "new"
    assert row.display_name_snapshot == "کالای اصلی"
    assert row.part_number_snapshot == "PN-OLD"
    assert row.cargo_type_fa_snapshot == "نوع"
    assert row.uom_symbol_snapshot == "ea"


def test_catalog_linked_creation_uses_catalog_values_not_payload_overrides(monkeypatch):
    cargo_type, uom = _master_data()
    catalog = CargoCatalogItem(
        id=10, public_id="catalog-public", organization_id=1, immutable_code="ITEM-1",
        fa_name="Catalog name", en_name="Catalog", cargo_type=cargo_type, default_uom=uom,
        part_number="PN-OLD", customer_item_code="C-OLD", hs_code="HS-OLD",
        brand="B-OLD", model="M-OLD", description="D-OLD", search_text="",
        is_active=True, version=1, created_by=7, updated_by=7,
    )
    row, _, _ = _capture_create(
        monkeypatch, catalog=catalog,
        overrides={"catalog_item_public_id": catalog.public_id},
    )
    assert row.part_number_snapshot == "PN-OLD"
    assert row.description_snapshot == "D-OLD"


def test_ordinary_update_changes_quantity_but_rejects_snapshot_rewrite(monkeypatch):
    row, _, _ = _capture_create(monkeypatch)
    row.version = 1
    monkeypatch.setattr(svc.db.session, "commit", lambda: None)
    updated = svc.update_shipment_item({"id": 7}, row, {"version": 1, "quantity": "5"})
    assert updated.quantity == svc.Decimal("5")
    assert updated.display_name_snapshot == "Manual cargo"
    with pytest.raises(svc.CargoError, match="snapshots cannot be changed"):
        svc.update_shipment_item({"id": 7}, row, {"version": 2, "display_name": "rewrite"})


def test_inactive_or_cross_organization_catalog_selection_fails_closed(monkeypatch):
    cargo_type, uom = _master_data()
    scalars = iter((cargo_type, uom))
    monkeypatch.setattr(svc.db.session, "scalar", lambda _query: next(scalars))
    monkeypatch.setattr(svc.operational_service, "require_permission", lambda *_args: None)
    monkeypatch.setattr(svc, "scoped_catalog", lambda *_args, **_kwargs: (_ for _ in ()).throw(svc.CargoError("not found", 404)))
    with pytest.raises(svc.CargoError) as exc:
        svc.create_shipment_item({"id": 7}, SimpleNamespace(id=99), {
            "line_number": 1, "cargo_type_public_id": cargo_type.public_id,
            "uom_public_id": uom.public_id, "quantity": "1",
            "catalog_item_public_id": "forbidden",
        })
    assert exc.value.status == 404


def test_version_conflict_and_positive_quantity_validation(monkeypatch):
    row, _, _ = _capture_create(monkeypatch)
    row.version = 3
    with pytest.raises(svc.CargoError, match="version conflict"):
        svc.update_shipment_item({"id": 7}, row, {"version": 2, "quantity": "2"})
    with pytest.raises(svc.CargoError, match="positive"):
        svc.update_shipment_item({"id": 7}, row, {"version": 3, "quantity": "0"})


def test_cargo_migration_is_additive_seed_free_and_scoped():
    migration = (Path(__file__).parents[1] / "migrations" / "versions" / "20260809_cargo_catalog_items.py").read_text(encoding="utf-8")
    assert 'revision = "20260809_cargo_catalog_items"' in migration
    assert 'down_revision = "20260808_reference_seed"' in migration
    assert "cargo_catalog_item" in migration and "cargo_item_alias" in migration and "shipment_cargo_item" in migration
    assert "description_snapshot" in migration
    assert "bulk_insert" not in migration and "op.execute" not in migration
    assert "shipment_request" not in migration and "ExecutionUnit" not in migration


def test_forbidden_capabilities_and_fields_are_absent_from_models_and_routes():
    root = Path(__file__).parents[1]
    source = (root / "cargo_models.py").read_text(encoding="utf-8") + (root / "routes" / "cargo.py").read_text(encoding="utf-8")
    for forbidden in ("ExecutionUnitCargoAllocation", "delivered_quantity", "allocation_quantity", "PackagingType", "pg_trgm"):
        assert forbidden not in source
