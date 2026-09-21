"""Audit persisted ADR-047 outcomes after the real-browser journeys."""
from __future__ import annotations

import json
import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


DATABASE_NAME = "forwarder_integrated_cert_fixed_shipment_owner_e2e"
HEAD = "20260926_fixed_shipment_responsible_expert"


def main() -> None:
    url = os.environ["DATABASE_URL"]
    parsed = make_url(url)
    if os.environ.get("APP_ENV") != "uat":
        raise RuntimeError("ADR-047 browser audit requires APP_ENV=uat")
    if parsed.host != "127.0.0.1" or parsed.database != DATABASE_NAME:
        raise RuntimeError("ADR-047 browser audit is restricted to its owned database")

    engine = create_engine(url)
    with engine.connect() as connection:
        assert connection.execute(text("SHOW server_version")).scalar_one().startswith("18.")
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD

        lineage = connection.execute(text("""
            SELECT s.id AS shipment_id,
                   s.public_id AS shipment_public_id,
                   s.primary_responsible_expert_id AS owner_id,
                   q.created_by_expert_id AS quote_issuer_id,
                   q.customer_response,
                   r.assigned_to AS request_assignee_id,
                   e1.username AS owner_username,
                   e2.username AS assignee_username
            FROM operational_shipment s
            JOIN expert_quote q ON q.id = s.accepted_quote_id
            JOIN shipment_request r ON r.id = s.shipment_request_id
            JOIN expert_user e1 ON e1.id = s.primary_responsible_expert_id
            JOIN expert_user e2 ON e2.id = r.assigned_to
        """)).mappings().one()
        assert lineage["owner_id"] == lineage["quote_issuer_id"]
        assert lineage["owner_id"] != lineage["request_assignee_id"]
        assert lineage["customer_response"] == "accepted"
        assert lineage["owner_username"] == "fixed_owner_e2e_e1"
        assert lineage["assignee_username"] == "fixed_owner_e2e_e2"

        nullability = connection.execute(text("""
            SELECT is_nullable FROM information_schema.columns
            WHERE table_schema='public'
              AND table_name='operational_shipment'
              AND column_name='primary_responsible_expert_id'
        """)).scalar_one()
        trigger_count = connection.execute(text("""
            SELECT COUNT(*)
            FROM pg_trigger t
            JOIN pg_class c ON c.oid=t.tgrelid
            WHERE c.relname='operational_shipment'
              AND t.tgname='trg_operational_shipment_fixed_owner'
              AND NOT t.tgisinternal
        """)).scalar_one()
        assert nullability == "NO"
        assert trigger_count == 1

        document = connection.execute(text("""
            SELECT COUNT(*) AS document_count,
                   MIN(uploaded_by) AS uploaded_by
            FROM case_document_file
            WHERE owner_type='SHIPMENT'
              AND operational_shipment_id=:shipment_id
              AND status='active'
        """), {"shipment_id": lineage["shipment_id"]}).mappings().one()
        assert document["document_count"] == 1
        assert document["uploaded_by"] == lineage["owner_id"]

        notification_actions = connection.execute(
            text("SELECT COUNT(*) FROM notification_action")
        ).scalar_one()
        notification_attempts = connection.execute(
            text("SELECT COUNT(*) FROM notification_attempt")
        ).scalar_one()
        assert notification_actions == 0
        assert notification_attempts == 0

    engine.dispose()
    print(json.dumps({
        "shipment_public_id": lineage["shipment_public_id"],
        "fixed_owner": lineage["owner_username"],
        "request_assignee": lineage["assignee_username"],
        "shipment_documents": document["document_count"],
        "postgresql": "18",
        "result": "PASS",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
