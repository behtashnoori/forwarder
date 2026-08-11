from __future__ import annotations

import inspect

import pytest

from backend import create_app
from backend.extensions import db
from backend.services import tracking_service
from backend.tenancy import (
    OwnershipScope,
    TenantContext,
    TenantContractError,
    assert_same_tenant,
    load_ownership_inventory,
    require_tenant_context,
    validate_inventory,
)


@pytest.fixture(scope="module")
def mapped_contract():
    app = create_app({"TESTING": True})
    with app.app_context():
        mappers = {mapper.class_.__name__: mapper for mapper in db.Model.registry.mappers}
        yield mappers, db.metadata


def _persisted_entries(inventory):
    return {
        name: entry
        for name, entry in inventory["entities"].items()
        if entry["kind"] == "persisted_model"
    }


def _follow_fk_path(mapper, metadata, owner_path):
    table = mapper.local_table
    segments = owner_path.split(".")
    assert len(segments) >= 2
    assert len(segments) == len(set(segments)), f"{owner_path}: ownership path must be acyclic"
    for segment in segments[:-1]:
        candidates = [
            column
            for column in table.c
            if any(fk.target_fullname.rsplit(".", 1)[0] == segment for fk in column.foreign_keys)
        ]
        assert len(candidates) == 1, f"{table.name} needs one unambiguous FK to {segment}"
        column = candidates[0]
        assert not column.nullable, f"{table.name}.{column.name} must be non-null"
        table = metadata.tables[segment]
    terminal = segments[-1]
    assert terminal in table.c, f"{table.name}: missing terminal {terminal}"
    assert not table.c[terminal].nullable, f"{table.name}.{terminal} must be non-null"
    return table


def test_inventory_schema_is_valid():
    inventory = load_ownership_inventory()
    assert inventory["classifications"] == [scope.value for scope in OwnershipScope]
    assert validate_inventory(inventory) == []


def test_every_mapped_model_and_association_table_is_classified(mapped_contract):
    mappers, metadata = mapped_contract
    inventory = load_ownership_inventory()
    persisted = _persisted_entries(inventory)
    assert set(persisted) == set(mappers)
    assert {entry["table"] for entry in persisted.values()} == {
        mapper.local_table.name for mapper in mappers.values()
    }
    association_entries = {
        entry["table"]
        for entry in inventory["entities"].values()
        if entry["kind"] == "association_table"
    }
    mapped_tables = {mapper.local_table.name for mapper in mappers.values()}
    assert association_entries == set(metadata.tables) - mapped_tables


def test_direct_resources_have_non_null_canonical_tenant_key(mapped_contract):
    mappers, _ = mapped_contract
    inventory = load_ownership_inventory()
    for name, entry in _persisted_entries(inventory).items():
        if entry["scope"] != OwnershipScope.TENANT_OWNED_DIRECT.value:
            continue
        assert entry["tenant_key"] == "organization_id"
        column = mappers[name].local_table.c[entry["tenant_key"]]
        assert not column.nullable, name


def test_indirect_resources_have_real_non_null_fk_owner_paths(mapped_contract):
    mappers, metadata = mapped_contract
    inventory = load_ownership_inventory()
    by_table = {entry["table"]: entry for entry in _persisted_entries(inventory).values()}
    for name, entry in _persisted_entries(inventory).items():
        if entry["scope"] == OwnershipScope.TENANT_OWNED_INDIRECT.value:
            owner_table = _follow_fk_path(mappers[name], metadata, entry["owner_path"])
            assert by_table[owner_table.name]["scope"] == OwnershipScope.TENANT_OWNED_DIRECT.value


def test_platform_scope_is_an_explicit_reasoned_allowlist():
    entries = load_ownership_inventory()["entities"]
    platform = [entry for entry in entries.values() if entry["scope"] == "PLATFORM_SCOPED"]
    assert platform
    assert all(entry.get("rationale") for entry in platform)


def test_ambiguous_resources_are_actionable_and_visible(capsys):
    entries = load_ownership_inventory()["entities"]
    ambiguous = sorted(name for name, entry in entries.items() if entry["scope"] == "LEGACY_AMBIGUOUS")
    print("LEGACY_AMBIGUOUS: " + ", ".join(ambiguous))
    assert ambiguous
    assert "ShipmentRequest" in ambiguous
    assert "CaseDocumentFile" in ambiguous
    assert "LEGACY_AMBIGUOUS" in capsys.readouterr().out


def test_public_capability_is_separate_from_underlying_resource():
    entries = load_ownership_inventory()["entities"]
    public = {name: entry for name, entry in entries.items() if entry["scope"] == "PUBLIC_CAPABILITY_SCOPED"}
    assert set(public) == {"PublicShipmentTrackingEndpoint"}
    assert public["PublicShipmentTrackingEndpoint"]["defect"] == "TENANT_ISOLATION_DEFECT"
    assert entries["ShipmentRequest"]["scope"] == "LEGACY_AMBIGUOUS"


def test_fail_closed_tenant_primitives():
    context = TenantContext(organization_id=11)
    assert require_tenant_context(context) is context
    assert_same_tenant(context, 11)
    with pytest.raises(TenantContractError):
        require_tenant_context(None)
    with pytest.raises(TenantContractError):
        assert_same_tenant(context, None)
    with pytest.raises(TenantContractError):
        assert_same_tenant(context, 12)


@pytest.mark.xfail(
    strict=True,
    reason="MT-3 defect: public tracking still accepts global numeric database IDs",
)
def test_public_tracking_rejects_numeric_ids_characterization():
    source = inspect.getsource(tracking_service.resolve_request)
    assert "identifier.isdigit()" not in source
    assert "ShipmentRequest.id" not in source
