"""Authorization's purpose-exclusive ADR-047 signer. No DB or staff JWT helper reuse."""
import base64
import hashlib
import re
import secrets
from uuid import UUID
from urllib.parse import urlsplit

import jwt

ISSUER = 'forwarder.quote-response.v1'
AUDIENCE = 'forwarder.quote-customer.v1'
TYPE = 'quote-response+jwt'
FIELDS = frozenset({'iss', 'aud', 'token_type', 'v', 'sub', 'jti', 'iat', 'nbf',
    'exp', 'tenant', 'request', 'quote', 'revision', 'content_digest'})
STATES = frozenset({'ACTIVE', 'VERIFY_ONLY', 'RETIRED', 'REVOKED', 'COMPROMISED'})
KID = re.compile(r'[A-Za-z0-9_-]{1,32}\Z', re.ASCII)


class CapabilityDenied(ValueError):
    """Allowlisted reason only; never attach token/material/provider exception."""


def customer_origins(config, *, testing=False):
    configured = config.get('QUOTE_CAPABILITY_ALLOWED_ORIGINS')
    if type(configured) not in {list, tuple} or not configured or len(configured) > 8:
        raise CapabilityDenied('ORIGIN_CONFIG')
    for origin in configured:
        if type(origin) is not str or not origin.isascii() or len(origin) > 255 or any(c.isspace() for c in origin):
            raise CapabilityDenied('ORIGIN_CONFIG')
        try:
            parsed = urlsplit(origin)
            port = parsed.port
            if (parsed.scheme not in {'http', 'https'} or not parsed.hostname
                    or not re.fullmatch(r'[A-Za-z0-9.-]+', parsed.hostname)
                    or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment
                    or origin != parsed.scheme + '://' + parsed.netloc
                    or (port is not None and not 1 <= port <= 65535)):
                raise ValueError
            if parsed.scheme == 'http' and not (testing and parsed.hostname in {'localhost', '127.0.0.1'}):
                raise ValueError
        except ValueError:
            raise CapabilityDenied('ORIGIN_CONFIG') from None
    return configured


def validate_claims(claims):
    if type(claims) is not dict or set(claims) != FIELDS:
        raise CapabilityDenied('CLAIM_SCHEMA')
    for field, expected in (('iss', ISSUER), ('aud', AUDIENCE),
                            ('token_type', 'quote-response')):
        if type(claims[field]) is not str or claims[field] != expected:
            raise CapabilityDenied('PURPOSE_DENIED')
    for field in ('v', 'revision', 'iat', 'nbf', 'exp'):
        if type(claims[field]) is not int:
            raise CapabilityDenied('CLAIM_TYPE')
    if claims['v'] != 1 or claims['revision'] != 1:
        raise CapabilityDenied('CLAIM_VERSION')
    if not (0 < claims['iat'] == claims['nbf'] < claims['exp'] <= 253402300799):
        raise CapabilityDenied('CLAIM_TIME')
    for field in ('sub', 'jti', 'tenant', 'request', 'quote'):
        value = claims[field]
        try:
            valid = type(value) is str and str(UUID(value)) == value
        except (ValueError, AttributeError, TypeError):
            valid = False
        if not valid:
            raise CapabilityDenied('CLAIM_ID')
    if type(claims['content_digest']) is not str or not re.fullmatch(
            r'[0-9a-f]{64}', claims['content_digest'], re.ASCII):
        raise CapabilityDenied('CLAIM_DIGEST')


def token_digest(token):
    return hashlib.sha256(token.encode('ascii')).hexdigest()


class QuoteKeyring:
    """Trusted complete configuration is admitted without fallback or secret output."""
    def __repr__(self):
        return '<QuoteKeyring: private material redacted>'

    def __init__(self, config):
        if jwt.__version__ != '2.13.0':
            raise CapabilityDenied('CRYPTO_VERSION_UNREVIEWED')
        entries = config.get('QUOTE_CAPABILITY_KEYRING')
        self.active = config.get('QUOTE_CAPABILITY_ACTIVE_KEY')
        self.epoch = config.get('QUOTE_CAPABILITY_POLICY_EPOCH')
        if (type(entries) is not dict or not entries or len(entries) > 16
                or type(self.epoch) is not int or self.epoch < 1
                or type(self.active) is not str or not KID.fullmatch(self.active)):
            raise CapabilityDenied('KEY_CONFIG')
        excluded = []
        for name in ('SECRET_KEY', 'JWT_SECRET_KEY'):
            value = config.get(name)
            if isinstance(value, str):
                excluded.append(value.encode('utf-8'))
                try:
                    excluded.append(base64.b64decode(value, validate=True))
                except (ValueError, TypeError):
                    pass
            elif isinstance(value, bytes):
                excluded.append(value)
        self._keys, self.states = {}, {}
        for kid, entry in entries.items():
            if (type(kid) is not str or not KID.fullmatch(kid) or type(entry) is not dict
                    or set(entry) != {'material', 'state'} or type(entry['state']) is not str or entry['state'] not in STATES
                    or type(entry['material']) is not str):
                raise CapabilityDenied('KEY_CONFIG')
            try:
                material = base64.b64decode(entry['material'], validate=True)
            except (ValueError, TypeError):
                raise CapabilityDenied('KEY_ENCODING') from None
            if (len(material) != 64 or base64.b64encode(material).decode('ascii') != entry['material']
                    or len(set(material)) < 16):
                raise CapabilityDenied('KEY_LENGTH_OR_PLACEHOLDER')
            if material in excluded or material in self._keys.values():
                raise CapabilityDenied('KEY_PURPOSE_REUSE')
            self._keys[kid], self.states[kid] = material, entry['state']
        if sorted(k for k, state in self.states.items() if state == 'ACTIVE') != [self.active]:
            raise CapabilityDenied('ACTIVE_KEY')

    def check_policy(self, policy):
        if (policy is None or policy.epoch != self.epoch or policy.active_key != self.active
                or policy.states != self.states):
            raise CapabilityDenied('KEY_POLICY_STALE')

    def _material(self, kid, *, new=False):
        if type(kid) is not str or not KID.fullmatch(kid):
            raise CapabilityDenied('KEY_UNKNOWN')
        if self.states.get(kid) not in ({'ACTIVE'} if new else {'ACTIVE', 'VERIFY_ONLY'}):
            raise CapabilityDenied('KEY_UNAVAILABLE')
        return self._keys[kid]

    def sign(self, claims, kid, *, new=False, expected_digest=None):
        validate_claims(claims)
        if new and kid != self.active:
            raise CapabilityDenied('KEY_NOT_ACTIVE')
        if not new and (type(expected_digest) is not str or not re.fullmatch('[0-9a-f]{64}', expected_digest)):
            raise CapabilityDenied('STORED_DIGEST_REQUIRED')
        token = jwt.encode({name: claims[name] for name in sorted(FIELDS)},
            self._material(kid, new=new), algorithm='HS256', headers={'typ': TYPE, 'kid': kid})
        if expected_digest is not None and not secrets.compare_digest(token_digest(token), expected_digest):
            raise CapabilityDenied('TOKEN_RECONSTRUCTION_MISMATCH')
        return token

    def verify(self, token):
        if type(token) is not str or not token.isascii() or len(token) > 4096:
            raise CapabilityDenied('TOKEN_MALFORMED')
        try:
            header = jwt.get_unverified_header(token)
            if (set(header) != {'alg', 'kid', 'typ'} or header['alg'] != 'HS256'
                    or header['typ'] != TYPE):
                raise CapabilityDenied('TOKEN_HEADER')
            key = self._material(header['kid'])
            claims = jwt.decode(token, key, algorithms=['HS256'], issuer=ISSUER,
                audience=AUDIENCE, leeway=0,
                options={'require': sorted(FIELDS), 'strict_aud': True})
            validate_claims(claims)
            return claims, header['kid']
        except (jwt.InvalidTokenError, OverflowError, TypeError, ValueError) as exc:
            if isinstance(exc, CapabilityDenied):
                raise
            raise CapabilityDenied('TOKEN_INVALID') from None
