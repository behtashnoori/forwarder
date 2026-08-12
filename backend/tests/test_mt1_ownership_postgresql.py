"""Disposable PostgreSQL certification for the MT-1 ownership expand graph."""
import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError


def _engine():
    url = os.getenv("MT1_OWNERSHIP_DATABASE_URL", "")
    if not url:
        pytest.skip("explicit disposable MT-1 ownership PostgreSQL URL not provided")
    assert "127.0.0.1" in url or "localhost" in url
    assert "/forwarder_mt1c_cert_ownership" in url
    return create_engine(url).execution_options(include_quarantined_for_certification=True)


def test_raw_sql_same_tenant_and_scope_constraints():
    engine = _engine()
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM expert_quote WHERE id IN (9101, 9102)"))
        connection.execute(text("DELETE FROM shipment_request WHERE id = 9101"))
        connection.execute(text("DELETE FROM expert_user WHERE id = 9101"))
        connection.execute(text("DELETE FROM operational_organization WHERE id IN (9101, 9102)"))
        connection.execute(text("INSERT INTO operational_organization (id, public_id, name, is_active, created_at) VALUES (9101, '00000000-0000-0000-0000-000000009101', 'A', true, now()), (9102, '00000000-0000-0000-0000-000000009102', 'B', true, now())"))
        connection.execute(text("INSERT INTO expert_user (id, username, password_hash, full_name, role, is_active, created_at) VALUES (9101, 'mt1-a', 'x', 'A', 'expert', true, now())"))
        connection.execute(text("INSERT INTO shipment_request (id, contact_phone, shipping_type, status, status_request_status, created_at, ready_at, operational_organization_id, ownership_scope) VALUES (9101, '09000009101', 'domestic', 'new', 'new', now(), now(), 9101, 'TENANT')"))
        connection.execute(text("INSERT INTO expert_quote (id, shipment_request_id, amount, currency, created_by_expert_id, created_at, operational_organization_id) VALUES (9101, 9101, 1, 'IRR', 9101, now(), 9101)"))

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO expert_quote (id, shipment_request_id, amount, currency, created_by_expert_id, created_at, operational_organization_id) VALUES (9102, 9101, 1, 'IRR', 9101, now(), 9102)"))

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO document_audit_event (event_type, scope_type) VALUES ('bad-tenant', 'TENANT')"))

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO document_audit_event (event_type, scope_type, operational_organization_id) VALUES ('bad-platform', 'PLATFORM', 9101)"))


def test_quote_constraint_is_deliberately_pending_validation():
    engine = _engine()
    with engine.connect() as connection:
        validated = connection.execute(text("SELECT convalidated FROM pg_constraint WHERE conname = 'fk_expert_quote_request_same_org'" )).scalar_one()
    assert validated is False


@pytest.mark.parametrize(
    ("table", "required"),
    [
        ("shipment_request", "contact_phone, shipping_type, status, status_request_status, created_at, ready_at"),
        ("customer", "first_name, last_name, created_at"),
    ],
)
def test_raw_sql_cannot_reuse_legacy_null_owner_exception(table, required):
    engine = _engine()
    values = (
        "'09000009999', 'domestic', 'new', 'new', now(), now()"
        if table == "shipment_request" else "'New', 'Ambiguous', now()"
    )
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(text(f"INSERT INTO {table} ({required}) VALUES ({values})"))
