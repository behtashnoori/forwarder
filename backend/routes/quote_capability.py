"""Customer capability API: no cookie/staff authentication or token-fetch endpoint."""
import json
from flask import Blueprint, current_app, jsonify, request
from backend.extensions import db
from backend.census_context import census_unit_of_work
from backend.security import rate_limit
from backend.services.governed_quote_service import customer_read, respond, QuoteConflict
from backend.services.quote_capability_crypto import CapabilityDenied, customer_origins
from backend.services.quote_response_authorization import ScopeChanged

quote_capability_bp = Blueprint('quote_capability', __name__, url_prefix='/api/quote-capability')


def is_capability_path(path):
    return path == '/api/quote-capability' or path.startswith('/api/quote-capability/')


def trusted_origins():
    return customer_origins(current_app.config, testing=current_app.testing)


@quote_capability_bp.before_request
def customer_boundary():
    try:
        allowed = trusted_origins()
        origin = request.headers.get('Origin')
        if origin is not None and origin not in allowed:
            raise CapabilityDenied('ORIGIN_DENIED')
        if request.method == 'POST' and request.headers.get('Sec-Fetch-Site') == 'cross-site':
            raise CapabilityDenied('ORIGIN_DENIED')
        if request.method == 'OPTIONS':
            if origin not in allowed or request.headers.get('Access-Control-Request-Method') not in {'GET', 'POST'}:
                raise CapabilityDenied('ORIGIN_DENIED')
            headers = {h.strip().lower() for h in request.headers.get('Access-Control-Request-Headers', '').split(',') if h.strip()}
            if headers - {'authorization', 'content-type', 'idempotency-key'}:
                raise CapabilityDenied('PREFLIGHT_HEADERS_DENIED')
            return '', 204
        if request.method == 'POST' and request.mimetype != 'application/json':
            return jsonify({'reason': 'JSON_REQUIRED'}), 415
    except (CapabilityDenied, ValueError):
        return jsonify({'reason': 'CUSTOMER_ACTION_UNAVAILABLE'}), 403


@quote_capability_bp.after_request
def customer_headers(response):
    for key in list(response.headers):
        if key[0].lower().startswith('access-control-'):
            response.headers.remove(key[0])
    try:
        origin = request.headers.get('Origin')
        if origin in trusted_origins():
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Authorization, Content-Type, Idempotency-Key'
            response.headers.add('Vary', 'Origin')
    except (CapabilityDenied, ValueError):
        pass
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    return response


def _token():
    header = request.headers.get('Authorization', '')
    if not header.startswith('QuoteCapability ') or len(header) > 4120 or header.count(' ') != 1:
        raise CapabilityDenied('AUTHORIZATION_REQUIRED')
    return header[len('QuoteCapability '):]


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('DUPLICATE_JSON_FIELD')
        value[key] = item
    return value


@quote_capability_bp.route('/quotes/<quote_public_id>', methods=['GET', 'POST', 'OPTIONS'])
@rate_limit(max_requests=60, per=60)
def quote_customer(quote_public_id):
    payload = None
    try:
        token = _token()
        if request.method == 'POST':
            raw = request.stream.read(2049)
            if len(raw) > 2048:
                return jsonify({'reason': 'BODY_TOO_LARGE'}), 413
            payload = json.loads(raw, object_pairs_hook=_unique_object)
        for attempt in range(3):
            db.session.rollback()
            try:
                with census_unit_of_work(db.session):
                    if request.method == 'GET':
                        result = customer_read(token, quote_public_id)
                        return jsonify(result)
                    result = respond(token, quote_public_id, payload, request.headers.get('Idempotency-Key'))
                    db.session.commit()
                    return jsonify(result)
            except ScopeChanged:
                db.session.rollback()
                if attempt == 2:
                    return jsonify({'reason': 'SCOPE_CHANGED_RETRY'}), 409
    except CapabilityDenied:
        db.session.rollback()
        return jsonify({'reason': 'CUSTOMER_ACTION_UNAVAILABLE'}), 403
    except QuoteConflict as exc:
        db.session.rollback()
        return jsonify({'reason': str(exc)}), 409
    except (ValueError, TypeError, UnicodeError):
        db.session.rollback()
        return jsonify({'reason': 'RESPONSE_PAYLOAD_INVALID'}), 400
    except Exception:
        db.session.rollback()
        current_app.logger.error('Quote capability request failed; request data suppressed')
        return jsonify({'reason': 'CUSTOMER_ACTION_FAILED'}), 500
