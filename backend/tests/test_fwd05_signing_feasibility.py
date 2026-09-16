"""Isolated library feasibility, NOT approval or runtime grant qualification.

All keys/tokens are ephemeral and never printed, persisted or delivered. This
probe tests the installed PyJWT primitive already used by backend.security.
"""
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import json
import re
import secrets
from uuid import uuid4, UUID

import jwt
import pytest

from backend import create_app
from backend.notification_provider import configured_provider


ISSUER = "forwarder.quote-response.v1"
AUDIENCE = "forwarder.quote-customer.v1"
TYPE = "quote-response+jwt"
FIELDS = {"iss", "aud", "token_type", "v", "sub", "jti", "iat", "nbf", "exp",
          "tenant", "request", "quote", "revision", "content_digest"}


class _PrivateMaterial(tuple):
    def __repr__(self):
        return "<synthetic ephemeral key fixture: redacted>"


def _schema(claims):
    """Probe the selected strict contract; not a product verifier."""
    if set(claims) != FIELDS:
        raise jwt.InvalidTokenError("CLAIM_SCHEMA")
    for field, expected in (("iss", ISSUER), ("aud", AUDIENCE),
                            ("token_type", "quote-response")):
        if type(claims[field]) is not str or claims[field] != expected:
            raise jwt.InvalidTokenError("PURPOSE_DENIED")
    for field in ("v", "revision", "iat", "nbf", "exp"):
        if type(claims[field]) is not int:
            raise jwt.InvalidTokenError("CLAIM_TYPE")
    if claims["v"] != 1 or claims["revision"] != 1:
        raise jwt.InvalidTokenError("CLAIM_VERSION")
    if not (0 < claims["iat"] == claims["nbf"] < claims["exp"] <= 253402300799):
        raise jwt.InvalidTokenError("CLAIM_TIME")
    for field in ("sub", "jti", "tenant", "request", "quote"):
        value = claims[field]
        if type(value) is not str:
            raise jwt.InvalidTokenError("CLAIM_ID")
        try:
            if str(UUID(value)) != value:
                raise ValueError()
        except ValueError:
            raise jwt.InvalidTokenError("CLAIM_ID") from None
    if type(claims["content_digest"]) is not str or not re.fullmatch(
            r"[0-9a-f]{64}", claims["content_digest"]):
        raise jwt.InvalidTokenError("CLAIM_DIGEST")


def _reconstruct(key, stored):
    _schema(stored)
    return _encode(key, {field: stored[field] for field in sorted(FIELDS)})


def _admit(encoded_ring, active, states, *, excluded=()):
    """Synthetic admission feasibility only; no operational configuration read."""
    if not encoded_ring or set(encoded_ring) != set(states):
        raise ValueError("KEY_CONFIG")
    decoded = {}
    for kid, encoded in encoded_ring.items():
        if type(kid) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", kid):
            raise ValueError("KEY_ID")
        if type(encoded) is not str:
            raise ValueError("KEY_ENCODING")
        try:
            value = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError):
            raise ValueError("KEY_ENCODING") from None
        if base64.b64encode(value).decode("ascii") != encoded or len(value) != 64:
            raise ValueError("KEY_LENGTH_ENCODING")
        if value in excluded or value in decoded.values():
            raise ValueError("KEY_PURPOSE_REUSE")
        if states[kid] not in {"ACTIVE", "VERIFY_ONLY", "RETIRED", "REVOKED", "COMPROMISED"}:
            raise ValueError("KEY_STATE")
        decoded[kid] = value
    if [kid for kid in states if states[kid] == "ACTIVE"] != [active]:
        raise ValueError("ACTIVE_KEY")
    return decoded


@pytest.fixture
def material():
    now = datetime.now(timezone.utc)
    claims = {
        "iss": ISSUER, "aud": AUDIENCE, "token_type": "quote-response",
        "v": 1, "sub": str(uuid4()), "jti": str(uuid4()),
        "iat": int(now.timestamp()), "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "tenant": str(uuid4()), "request": str(uuid4()),
        "quote": str(uuid4()), "revision": 1,
        "content_digest": hashlib.sha256(b"synthetic-content").hexdigest(),
    }
    return _PrivateMaterial((secrets.token_bytes(64), secrets.token_bytes(64), claims))


def _encode(key, claims, *, typ=TYPE, algorithm="HS256"):
    return jwt.encode(claims, key, algorithm=algorithm, headers={"typ": typ, "kid": "ephemeral_v1"})


def _decode(token, key):
    # Fixed algorithms; no algorithm, URL or key lookup chosen by the token.
    if type(token) is not str or len(token.encode("utf-8")) > 4096:
        raise jwt.InvalidTokenError("TOKEN_SIZE")
    header = jwt.get_unverified_header(token)
    if (set(header) != {"typ", "kid", "alg"} or header.get("typ") != TYPE
            or header.get("alg") != "HS256" or header.get("kid") != "ephemeral_v1"):
        raise jwt.InvalidTokenError("HEADER_SCHEMA")
    value = jwt.decode(token, key, algorithms=["HS256"], issuer=ISSUER,
        audience=AUDIENCE, leeway=0,
        options={"require": sorted(FIELDS), "strict_aud": True})
    _schema(value)
    return value


def test_persisted_json_order_and_integer_epochs_reconstruct_exact_digest(material):
    key, _, claims = material
    issued = _reconstruct(key, claims)
    digest = hashlib.sha256(issued.encode("ascii")).digest()
    for stored in (json.loads(json.dumps(claims)),
                   json.loads(json.dumps(claims, sort_keys=True)),
                   dict(reversed(list(json.loads(json.dumps(claims)).items())))):
        reconstructed = _reconstruct(key, stored)
        assert secrets.compare_digest(digest, hashlib.sha256(reconstructed.encode("ascii")).digest())
        assert reconstructed == issued
        assert _decode(reconstructed, key) == claims


@pytest.mark.parametrize("field,value", [
    ("iat", "1"), ("iat", True), ("nbf", False), ("exp", 253402300800),
    ("revision", True), ("v", 1.0), ("v", 2), ("revision", 2),
    ("aud", [AUDIENCE]), ("tenant", 42), ("quote", "../key"),
    ("jti", None), ("content_digest", "A" * 64), ("content_digest", "bad"),
])
def test_signed_nonstrict_claims_rejected(material, field, value):
    key, _, claims = material
    with pytest.raises(jwt.InvalidTokenError):
        _decode(_encode(key, {**claims, field: value}), key)


@pytest.mark.parametrize("field", sorted(FIELDS))
def test_all_scope_fields_required(material, field):
    key, _, claims = material
    with pytest.raises(jwt.InvalidTokenError):
        _decode(_encode(key, {k: v for k, v in claims.items() if k != field}), key)


def test_extra_claims_headers_unknown_key_and_size_rejected(material):
    key, _, claims = material
    tokens = [_encode(key, {**claims, "staff": True}), "x" * 4097]
    with pytest.raises(jwt.InvalidTokenError):
        jwt.encode(claims, key, algorithm="HS256", headers={"typ": TYPE, "kid": None})
    for headers in ({"kid": "unknown"}, {"kid": "../key"},
                    {"jku": "https://example.invalid/key"}, {"crit": ["custom"]}):
        tokens.append(jwt.encode(claims, key, algorithm="HS256",
            headers={"typ": TYPE, "kid": "ephemeral_v1", **headers}))
    for token in tokens:
        with pytest.raises(jwt.InvalidTokenError):
            _decode(token, key)


def test_synthetic_key_admission_has_no_fallback_or_purpose_reuse(material):
    key, staff, _ = material
    encoded = base64.b64encode(key).decode("ascii")
    assert _admit({"new": encoded}, "new", {"new": "ACTIVE"})["new"] == key
    failures = [({}, "new", {}, ()),
        ({"new": "placeholder"}, "new", {"new": "ACTIVE"}, ()),
        ({"new": base64.b64encode(staff[:16]).decode()}, "new", {"new": "ACTIVE"}, ()),
        ({"new": encoded}, "new", {"new": "ACTIVE"}, (key,)),
        ({"new": encoded, "old": encoded}, "new", {"new": "ACTIVE", "old": "VERIFY_ONLY"}, ()),
        ({"../new": encoded}, "../new", {"../new": "ACTIVE"}, ()),
        ({"new": encoded}, "missing", {"new": "ACTIVE"}, ()),
        ({"new": encoded}, "new", {"new": "COMPROMISED"}, ())]
    for ring, active, states, excluded in failures:
        with pytest.raises(ValueError):
            _admit(ring, active, states, excluded=excluded)


def test_installed_primitive_can_bind_exact_claims_and_reconstruct(material):
    key, _, claims = material
    first = _encode(key, claims)
    assert first == _encode(key, claims)
    decoded = _decode(first, key)
    for field in ("tenant", "request", "quote", "revision", "content_digest", "sub", "jti"):
        assert decoded[field] == claims[field]


def test_staff_signing_key_cannot_verify_quote_token(material):
    key, staff_key, claims = material
    with pytest.raises(jwt.InvalidSignatureError):
        _decode(_encode(key, claims), staff_key)


def test_staff_token_signed_by_another_purpose_key_is_rejected(material):
    key, staff_key, claims = material
    with pytest.raises(jwt.InvalidTokenError):
        _decode(_encode(staff_key, {**claims, "token_type": "access"}), key)


@pytest.mark.parametrize("field,value", [
    ("iss", "forwarder.staff"), ("aud", "forwarder.staff"),
    ("token_type", "access"), ("token_type", "refresh"),
])
def test_signed_wrong_purpose_claims_are_rejected(material, field, value):
    key, _, claims = material
    with pytest.raises(jwt.InvalidTokenError):
        _decode(_encode(key, {**claims, field: value}), key)


def test_wrong_header_type_is_rejected(material):
    key, _, claims = material
    with pytest.raises(jwt.InvalidTokenError):
        _decode(_encode(key, claims, typ="JWT"), key)


@pytest.mark.parametrize("missing", ["iss", "aud", "exp", "nbf", "iat", "sub", "jti"])
def test_mandatory_claims_are_required(material, missing):
    key, _, claims = material
    with pytest.raises(jwt.InvalidTokenError):
        _decode(_encode(key, {k: v for k, v in claims.items() if k != missing}), key)


def test_expiry_and_not_before_have_no_staff_skew(material):
    key, _, claims = material
    with pytest.raises(jwt.ExpiredSignatureError):
        _decode(_encode(key, {**claims, "exp": datetime.now(timezone.utc) - timedelta(seconds=1)}), key)
    with pytest.raises(jwt.ImmatureSignatureError):
        _decode(_encode(key, {**claims, "nbf": datetime.now(timezone.utc) + timedelta(minutes=1)}), key)


def test_algorithm_allowlist_and_malformed_input(material):
    key, _, claims = material
    for token in ("not-a-token", _encode(key, claims, algorithm="HS384"),
                  jwt.encode(claims, "", algorithm="none")):
        with pytest.raises(jwt.InvalidTokenError):
            _decode(token, key)


def test_fake_provider_requires_all_three_explicit_runtime_gates():
    for testing, provider, environment in (
        (True, "fake", "qualification"), (True, "fake", "development"),
        (True, None, "qualification"),
    ):
        app = create_app({"TESTING": testing, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "NOTIFICATION_PROVIDER": provider, "NOTIFICATION_ENVIRONMENT": environment}, skip_startup=True)
        with app.app_context():
            if provider == "fake" and environment == "qualification":
                assert configured_provider().simulated is True
                # Test configuration cannot override the synthetic-destination guard.
                result = configured_provider().send(reference="synthetic-probe",
                    recipient="synthetic@external.invalid", template="probe")
                assert result.outcome == "FAILED" and result.reason == "SYNTHETIC_RECIPIENT_REQUIRED"
            else:
                with pytest.raises(ValueError, match="EXPLICIT_FAKE_QUALIFICATION_REQUIRED"):
                    configured_provider()
