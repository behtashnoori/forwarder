"""Test referral engine (round-robin auto-assign) and admin preview API."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def run_tests():
    from backend import create_app
    from backend.extensions import db
    from backend.models import (
        ExpertUser,
        ShipmentRequest,
        ReferralAssignmentLog,
        ReferralAutoAssignState,
        ExpertConsoleLog,
        Province,
    )
    from backend.referral_engine import referral_engine

    overrides = {"TESTING": True}
    if os.environ.get("TEST_DATABASE_URL"):
        overrides["SQLALCHEMY_DATABASE_URI"] = os.environ["TEST_DATABASE_URL"]
    app = create_app(overrides)
    with app.app_context():
        if os.environ.get("TEST_DATABASE_URL"):
            db.create_all()
        errors = []

        # Ensure at least one expert
        experts = db.session.query(ExpertUser).filter(
            ExpertUser.role.in_(["expert", "business_expert"]),
            ExpertUser.is_active == True,
        ).all()
        if not experts:
            try:
                import bcrypt
                pw = bcrypt.hashpw(b"test123", bcrypt.gensalt()).decode("utf-8")
            except Exception:
                from werkzeug.security import generate_password_hash
                pw = generate_password_hash("test123", method="pbkdf2:sha256")
            e1 = ExpertUser(
                username="expert1_referral_test",
                password_hash=pw,
                full_name="Expert One",
                email="e1@test.com",
                role="expert",
                is_active=True,
            )
            db.session.add(e1)
            db.session.commit()
            experts = [e1]

        province = db.session.query(Province).first()
        pid = province.id if province else None

        # Ensure auto-assign state row exists
        state = db.session.query(ReferralAutoAssignState).filter(ReferralAutoAssignState.id == 1).first()
        if not state:
            from datetime import datetime, timezone
            state = ReferralAutoAssignState(id=1, last_index=0, updated_at=datetime.now(timezone.utc))
            db.session.add(state)
            db.session.commit()

        # Create a new request and auto-assign
        req = ShipmentRequest(
            shipping_type="domestic",
            domestic_transport_method="road",
            international_transport_method=None,
            transport_method="road",
            origin_province_id=pid,
            dest_province_id=pid,
            contact_phone="09121234567",
            status="new",
            assigned_to=None,
        )
        db.session.add(req)
        db.session.commit()
        request_id = req.id

        try:
            expert_id = referral_engine.auto_assign_request(request_id)
            if not expert_id:
                errors.append("auto_assign_request returned None")
            else:
                req = db.session.get(ShipmentRequest, request_id)
                if req.status != "assigned" or req.assigned_to != expert_id:
                    errors.append(f"Request not assigned: status={req.status} assigned_to={req.assigned_to}")
                if expert_id not in [e.id for e in experts]:
                    errors.append(f"Assigned expert {expert_id} not in experts list")
                log = db.session.query(ReferralAssignmentLog).filter(
                    ReferralAssignmentLog.request_id == request_id,
                ).first()
                if not log:
                    errors.append("ReferralAssignmentLog not created")
                elif log.strategy_used not in ("direct", "round_robin", "least_workload"):
                    errors.append(f"Unexpected strategy_used={log.strategy_used}")
                # Auto-assign must create ExpertConsoleLog for timeline consistency
                console_log = db.session.query(ExpertConsoleLog).filter(
                    ExpertConsoleLog.shipment_request_id == request_id,
                    ExpertConsoleLog.action == "assignment",
                ).first()
                if not console_log:
                    errors.append("ExpertConsoleLog (action=assignment) not created on auto-assign")
        except Exception as e:
            errors.append(f"auto_assign_request raised: {e}")
            import traceback
            traceback.print_exc()

        # Preview (dry run)
        preview = referral_engine.preview_assignment(request_id)
        if preview.get("error") == "request_not_found":
            errors.append("preview returned request_not_found for existing request")
        if not preview.get("error") and preview.get("strategy_used") not in ("direct", "round_robin", "least_workload"):
            errors.append(f"Preview returned unexpected strategy_used={preview.get('strategy_used')}")

        # Admin API: GET referral-rules (may be empty), POST preview
        admin = db.session.query(ExpertUser).filter(ExpertUser.role == "admin").first()
        if admin:
            client = app.test_client()
            login_resp = client.post(
                "/api/expert/auth/login",
                json={"username": admin.username, "password": "test123"},
            )
            if login_resp.status_code == 200:
                data = login_resp.get_json()
                token = (data.get("tokens") or {}).get("access_token")
                if token:
                    get_rules = client.get(
                        "/api/admin/referral-rules",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    if get_rules.status_code != 200:
                        errors.append(f"GET referral-rules failed: {get_rules.status_code}")
                    elif "referral_rules" not in (get_rules.get_json() or {}):
                        errors.append("GET referral-rules: missing referral_rules key")
                    preview_resp = client.post(
                        "/api/admin/referral-rules/preview",
                        json={"request_id": request_id},
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    if preview_resp.status_code != 200:
                        errors.append(f"POST referral-rules/preview failed: {preview_resp.status_code}")

        if errors:
            print("Errors:", errors)
        else:
            print("All referral engine and API checks passed.")
        return errors


def test_referral_engine_and_api():
    """Pytest entry point."""
    errs = run_tests()
    assert not errs, f"Referral tests failed: {errs}"


if __name__ == "__main__":
    errs = run_tests()
    sys.exit(1 if errs else 0)
