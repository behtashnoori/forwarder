"""Admin policy read/write and Commercial-owned currency catalog read."""
from flask import Blueprint, g, jsonify, request
from backend.extensions import db
from backend.security import require_auth
from backend.services.admin_authorization_service import require_organization_admin_context
from backend.services.quotation_settings_service import set_quotation_timezone
from backend.services.quote_capability_crypto import CapabilityDenied
from backend.services.governed_quote_service import CURRENCIES
from backend.operational_models import OperationalOrganization

quotation_settings_bp = Blueprint('quotation_settings', __name__, url_prefix='/api')


@quotation_settings_bp.get('/commercial/quote-currencies')
@require_auth
def quote_currencies():
    return jsonify({'money_contract': 'quote-major.v1', 'items': list(CURRENCIES)})


@quotation_settings_bp.route('/admin/quotation-settings', methods=['GET', 'PATCH'])
@require_organization_admin_context(allow_platform=False)
def quotation_settings():
    context = g.organization_context
    if request.method == 'GET':
        org = db.session.get(OperationalOrganization, context.organization_id)
        return jsonify({'timezone': org.quotation_validity_timezone, 'configured': org.quotation_validity_timezone is not None})
    payload = request.get_json(silent=True)
    if type(payload) is not dict or set(payload) != {'timezone'}:
        return jsonify({'reason': 'TIMEZONE_PAYLOAD_INVALID'}), 400
    try:
        result = set_quotation_timezone(g.current_user_id, context.organization_id, payload['timezone'])
        db.session.commit()
        return jsonify(result)
    except CapabilityDenied:
        db.session.rollback()
        return jsonify({'reason': 'ORGANIZATION_ADMIN_REQUIRED'}), 403
    except ValueError:
        db.session.rollback()
        return jsonify({'reason': 'IANA_TIMEZONE_INVALID'}), 400
