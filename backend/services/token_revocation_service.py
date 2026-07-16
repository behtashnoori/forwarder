"""JWT revocation storage and cleanup helpers."""
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from backend.extensions import db
from backend.models import RevokedToken


def is_token_revoked(jti: str) -> bool:
    return db.session.query(RevokedToken.id).filter_by(jti=jti).first() is not None


def revoke_payload(payload: dict, reason: str = "logout") -> bool:
    jti, expires_at, token_type = payload.get("jti"), payload.get("exp"), payload.get("token_type")
    if not isinstance(jti, str) or not jti or not isinstance(expires_at, (int, float)):
        raise ValueError("token payload is not revocable")
    if token_type not in {"access", "refresh"}:
        raise ValueError("unsupported token type")
    if is_token_revoked(jti):
        return False
    db.session.add(RevokedToken(
        jti=jti, user_id=payload.get("user_id"), token_type=token_type,
        expires_at=datetime.fromtimestamp(expires_at, tz=timezone.utc).replace(tzinfo=None), reason=reason,
    ))
    try:
        db.session.commit()
        return True
    except IntegrityError:
        db.session.rollback()
        return False


def cleanup_expired(*, now: datetime | None = None, dry_run: bool = True) -> int:
    query = RevokedToken.query.filter(RevokedToken.expires_at <= (now or datetime.utcnow()))
    count = query.count()
    if not dry_run and count:
        query.delete(synchronize_session=False)
        db.session.commit()
    return count
