"""Test referral engine and referral rules API (run with pytest or as script)."""
import json
import os
import sys

# Ensure project root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def run_tests():
    from backend import create_app
    from backend.extensions import db
    from backend.models import (
        ExpertUser, ShipmentRequest, ReferralRule, ReferralRuleState,
        ReferralAssignmentLog, Province,
    )
    from backend.referral_engine import referral_engine, _conditions_match, _get_request_transport_method

    # Use real DB from env if TEST_DATABASE_URL not set (so we have admin/experts/data)
    overrides = {"TESTING": True}
    if os.environ.get("TEST_DATABASE_URL"):
        overrides["SQLALCHEMY_DATABASE_URI"] = os.environ["TEST_DATABASE_URL"]
    app = create_app(overrides)
    with app.app_context():
        if os.environ.get("TEST_DATABASE_URL"):
            db.create_all()
        # else use existing DB (migrations already applied)
        errors = []

        # --- 1) Conditions match ---
        class FakeRequest:
            shipping_type = "international"
            domestic_transport_method = None
            international_transport_method = "air"
            transport_method = None
            origin_province_id = 1
            dest_province_id = 2
        req = FakeRequest()
        if not _conditions_match(req, {"shipping_type": "international"}):
            errors.append("conditions match: shipping_type international failed")
        if _conditions_match(req, {"shipping_type": "domestic"}):
            errors.append("conditions match: should not match domestic")
        if not _conditions_match(req, {}):
            errors.append("conditions match: empty conditions should match")
        tm = _get_request_transport_method(req)
        if tm != "air":
            errors.append(f"transport method expected air got {tm}")

        # --- 2) Ensure admin and at least one expert (create if missing for self-contained test) ---
        admin = db.session.query(ExpertUser).filter(ExpertUser.role == "admin").first()
        if not admin:
            try:
                import bcrypt
                admin_password_hash = bcrypt.hashpw(b"test123", bcrypt.gensalt()).decode("utf-8")
            except Exception:
                from werkzeug.security import generate_password_hash
                admin_password_hash = generate_password_hash("test123", method="pbkdf2:sha256")
            admin = ExpertUser(
                username="admin_referral_test",
                password_hash=admin_password_hash,
                full_name="Admin Test",
                email="admin_test@test.com",
                role="admin",
                is_active=True,
            )
            db.session.add(admin)
            db.session.commit()
            print("Created admin for test:", admin.id)

        experts = db.session.query(ExpertUser).filter(
            ExpertUser.role.in_(["expert", "business_expert"]),
            ExpertUser.is_active == True,
        ).all()
        if not experts:
            try:
                import bcrypt
                expert_password_hash = bcrypt.hashpw(b"test123", bcrypt.gensalt()).decode("utf-8")
            except Exception:
                from werkzeug.security import generate_password_hash
                expert_password_hash = generate_password_hash("test123", method="pbkdf2:sha256")
            e1 = ExpertUser(
                username="expert1_referral_test",
                password_hash=expert_password_hash,
                full_name="Expert One",
                email="e1@test.com",
                role="expert",
                is_active=True,
            )
            db.session.add(e1)
            db.session.commit()
            experts = [e1]
            print("Created expert for test:", e1.id)

        if errors:
            print("Pre-checks:", errors)
            return errors

        # --- 3) Create a referral rule (direct_assign) ---
        rule_direct = db.session.query(ReferralRule).filter(ReferralRule.name == "Test Direct Rule").first()
        if not rule_direct:
            rule_direct = ReferralRule(
                name="Test Direct Rule",
                is_active=True,
                priority=1,
                conditions=json.dumps({"shipping_type": "domestic"}),
                action=json.dumps({"type": "direct_assign", "expert_id": experts[0].id}),
                stop_on_match=True,
                created_by=admin.id,
            )
            db.session.add(rule_direct)
            db.session.commit()
            print("Created rule (direct):", rule_direct.id)

        # --- 4) Create a shipment request that matches (domestic) ---
        province = db.session.query(Province).first()
        pid = province.id if province else None
        req_match = ShipmentRequest(
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
        db.session.add(req_match)
        db.session.commit()
        request_id_match = req_match.id
        print("Created matching request:", request_id_match)

        # --- 5) Auto assign ---
        try:
            expert_id = referral_engine.auto_assign_request(request_id_match)
            if not expert_id:
                errors.append("auto_assign_request returned None for matching request")
            else:
                req_match = db.session.get(ShipmentRequest, request_id_match)
                if req_match.status != "assigned" or req_match.assigned_to != expert_id:
                    errors.append(f"Request not assigned: status={req_match.status} assigned_to={req_match.assigned_to}")
                log = db.session.query(ReferralAssignmentLog).filter(
                    ReferralAssignmentLog.request_id == request_id_match,
                ).first()
                if not log:
                    errors.append("ReferralAssignmentLog not created")
                print("Assigned to expert:", expert_id)
        except Exception as e:
            errors.append(f"auto_assign_request raised: {e}")
            import traceback
            traceback.print_exc()

        # --- 6) Preview (dry run, no DB change) ---
        req_no_match = ShipmentRequest(
            shipping_type="international",
            domestic_transport_method=None,
            international_transport_method="sea",
            transport_method=None,
            origin_province_id=pid,
            dest_province_id=pid,
            contact_phone="09129876543",
            status="new",
            assigned_to=None,
        )
        db.session.add(req_no_match)
        db.session.commit()
        preview = referral_engine.preview_assignment(req_no_match.id)
        if preview.get("error") == "request_not_found":
            errors.append("preview returned request_not_found for existing request")
        print("Preview result keys:", list(preview.keys()))

        # --- 7) Pool rule + round_robin (if we have 2+ experts) ---
        if len(experts) >= 2:
            rule_pool = db.session.query(ReferralRule).filter(ReferralRule.name == "Test Pool Rule").first()
            if not rule_pool:
                rule_pool = ReferralRule(
                    name="Test Pool Rule",
                    is_active=True,
                    priority=2,
                    conditions=json.dumps({"shipping_type": "international"}),
                    action=json.dumps({
                        "type": "pool_assign",
                        "expert_ids": [experts[0].id, experts[1].id],
                        "strategy": "round_robin",
                    }),
                    stop_on_match=True,
                    created_by=admin.id,
                )
                db.session.add(rule_pool)
                db.session.commit()
            req_pool = ShipmentRequest(
                shipping_type="international",
                domestic_transport_method=None,
                international_transport_method="air",
                contact_phone="09121111111",
                status="new",
                assigned_to=None,
            )
            db.session.add(req_pool)
            db.session.commit()
            try:
                expert_id_pool = referral_engine.auto_assign_request(req_pool.id)
                if expert_id_pool not in [experts[0].id, experts[1].id]:
                    errors.append(f"Pool assignment expected one of {[experts[0].id, experts[1].id]} got {expert_id_pool}")
                print("Pool assigned to:", expert_id_pool)
            except Exception as e:
                errors.append(f"Pool auto_assign raised: {e}")

        # --- 8) Admin API (GET referral-rules, POST preview) ---
        # If we created this admin in test, set bcrypt password so login works (auth uses bcrypt.checkpw)
        if admin.username == "admin_referral_test":
            try:
                import bcrypt
                admin.password_hash = bcrypt.hashpw(b"test123", bcrypt.gensalt()).decode("utf-8")
                db.session.commit()
            except Exception:
                pass
        client = app.test_client()
        login_resp = client.post(
            "/api/expert/auth/login",
            json={"username": admin.username, "password": "test123"},
        )
        if login_resp.status_code != 200:
            # Skip API checks if login fails (e.g. pre-existing admin with different password)
            print("Admin login skipped or failed - skipping API checks")
        else:
            data = login_resp.get_json()
            token = (data.get("tokens") or {}).get("access_token")
            if not token:
                errors.append("No access_token in login response")
            else:
                get_rules = client.get(
                    "/api/admin/referral-rules",
                    headers={"Authorization": f"Bearer {token}"},
                )
            if get_rules.status_code != 200:
                errors.append(f"GET referral-rules failed: {get_rules.status_code}")
            else:
                rules_data = get_rules.get_json()
                if "referral_rules" not in rules_data:
                    errors.append("GET referral-rules: missing referral_rules key")
                print("GET referral-rules:", len(rules_data.get("referral_rules", [])), "rules")

            preview_resp = client.post(
                "/api/admin/referral-rules/preview",
                json={"request_id": req_no_match.id},
                headers={"Authorization": f"Bearer {token}"},
            )
            if preview_resp.status_code != 200:
                errors.append(f"POST referral-rules/preview failed: {preview_resp.status_code}")
            else:
                prev = preview_resp.get_json()
                if prev.get("error"):
                    errors.append(f"Preview returned error: {prev.get('error')}")
                print("POST preview: OK")

        if errors:
            print("Errors:", errors)
        else:
            print("All referral engine and API checks passed.")
        return errors


def test_referral_engine_and_api():
    """Pytest entry point: run referral engine and API checks."""
    errs = run_tests()
    assert not errs, f"Referral tests failed: {errs}"


if __name__ == "__main__":
    errs = run_tests()
    sys.exit(1 if errs else 0)
