"""Audit persisted outcomes from the owned Quote communication browser run."""
from __future__ import annotations

import json
import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def main() -> None:
    url = os.environ["DATABASE_URL"]
    parsed = make_url(url)
    if os.environ.get("APP_ENV") != "uat":
        raise RuntimeError("Quote communication browser audit requires APP_ENV=uat")
    if parsed.host != "127.0.0.1" or parsed.database != "forwarder_integrated_cert_quote_communication_e2e":
        raise RuntimeError("Quote communication browser audit is restricted to its owned database")

    engine = create_engine(url)
    with engine.connect() as connection:
        summary = connection.execute(text("""
            SELECT
                COUNT(*) AS quote_count,
                COUNT(*) FILTER (WHERE customer_response = 'accepted') AS accepted_count,
                COUNT(*) FILTER (WHERE customer_response = 'discussion') AS discussion_count,
                COUNT(*) FILTER (WHERE customer_response = 'declined') AS declined_count,
                COUNT(DISTINCT public_id) AS opaque_quote_count
            FROM expert_quote
        """)).mappings().one()
        assert dict(summary) == {
            "quote_count": 4,
            "accepted_count": 2,
            "discussion_count": 1,
            "declined_count": 1,
            "opaque_quote_count": 4,
        }

        discussion_history = connection.execute(text("""
            SELECT q.amount, q.currency, q.customer_response,
                   q.customer_response_message, q.responded_by_customer_id
            FROM expert_quote q
            JOIN shipment_request r ON r.id=q.shipment_request_id
            WHERE r.tracking_code='QC-E2E-DISCUSSION'
            ORDER BY q.created_at, q.id
        """)).mappings().all()
        assert len(discussion_history) == 2
        assert dict(discussion_history[0]) == {
            "amount": 1_270_000,
            "currency": "EUR",
            "customer_response": "discussion",
            "customer_response_message": "لطفاً شرایط پرداخت و زمان تحویل را هماهنگ کنیم",
            "responded_by_customer_id": 910002,
        }
        assert discussion_history[1]["amount"] == 1_500_000
        assert discussion_history[1]["currency"] == "USD"
        assert discussion_history[1]["customer_response"] == "accepted"

        audit_count = connection.execute(text("""
            SELECT COUNT(*) FROM expert_console_log
            WHERE action='customer_quote_response'
        """)).scalar_one()
        leaked_message_count = connection.execute(text("""
            SELECT COUNT(*) FROM expert_console_log
            WHERE action='customer_quote_response'
              AND note LIKE '%شرایط پرداخت%'
        """)).scalar_one()
        cargo_count = connection.execute(text("SELECT COUNT(*) FROM request_cargo_item")).scalar_one()
        notification_actions = connection.execute(text("SELECT COUNT(*) FROM notification_action")).scalar_one()
        notification_attempts = connection.execute(text("SELECT COUNT(*) FROM notification_attempt")).scalar_one()
        local_console_notifications = connection.execute(text("SELECT COUNT(*) FROM expert_console_notification")).scalar_one()

        assert audit_count == 4
        assert leaked_message_count == 0
        assert cargo_count == 2
        assert notification_actions == 0
        assert notification_attempts == 0
        # The official Quote revision retains the pre-existing local expert-console notice.
        assert local_console_notifications == 1

    engine.dispose()
    print(json.dumps({
        "quote_count": summary["quote_count"],
        "response_audit_count": audit_count,
        "notification_actions": notification_actions,
        "notification_attempts": notification_attempts,
        "local_console_notifications": local_console_notifications,
        "result": "PASS",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
