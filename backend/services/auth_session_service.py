"""Server-side authentication session lifecycle and refresh rotation."""
from datetime import datetime, timezone
from uuid import uuid4

from flask import current_app

from backend.extensions import db
from backend.models import AuthSession, ExpertUser, RevokedToken
from backend.security import security


def _expires_at(exp: int | float) -> datetime:
    return datetime.fromtimestamp(exp, tz=timezone.utc).replace(tzinfo=None)


def _add_revocation(payload: dict, reason: str) -> None:
    jti = payload.get("jti")
    if not jti or RevokedToken.query.filter_by(jti=jti).first():
        return
    db.session.add(RevokedToken(
        jti=jti,
        user_id=payload.get("user_id"),
        token_type=payload.get("token_type"),
        expires_at=_expires_at(payload["exp"]),
        reason=reason,
    ))


def _token_pair(user_id: int, session_id: str, refresh_jti: str) -> dict[str, str]:
    access = security.generate_token(user_id, "access", session_id=session_id)
    refresh = security.generate_token(
        user_id,
        "refresh",
        session_id=session_id,
        jti=refresh_jti,
    )
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "Bearer",
        "expires_in": int(current_app.config["JWT_ACCESS_TOKEN_EXPIRES"].total_seconds()),
    }


def create_session_tokens(user_id: int) -> dict[str, str]:
    session_id = str(uuid4())
    refresh_jti = str(uuid4())
    now = datetime.utcnow()
    session = AuthSession(
        session_id=session_id,
        user_id=user_id,
        refresh_jti=refresh_jti,
        created_at=now,
        last_rotated_at=now,
        expires_at=now + current_app.config["JWT_REFRESH_TOKEN_EXPIRES"],
        is_active=True,
    )
    db.session.add(session)
    db.session.commit()
    return _token_pair(user_id, session_id, refresh_jti)


def is_session_active(session_id: str, user_id: int | None) -> bool:
    now = datetime.utcnow()
    return db.session.query(AuthSession.id).filter(
        AuthSession.session_id == session_id,
        AuthSession.user_id == user_id,
        AuthSession.is_active.is_(True),
        AuthSession.revoked_at.is_(None),
        AuthSession.expires_at > now,
    ).first() is not None


def rotate_refresh_token(raw_refresh_token: str) -> dict[str, str] | None:
    payload = security.verify_token(raw_refresh_token)
    if not payload or payload.get("token_type") != "refresh":
        return None
    session_id, refresh_jti, user_id = payload.get("sid"), payload.get("jti"), payload.get("user_id")
    if not session_id or not refresh_jti or not user_id:
        return None
    session = AuthSession.query.filter_by(session_id=session_id, user_id=user_id).with_for_update().first()
    if not session:
        return None
    user = db.session.get(ExpertUser, user_id)
    if not user or not user.is_active or not session.is_active or session.revoked_at or session.expires_at <= datetime.utcnow():
        return None
    if session.refresh_jti != refresh_jti:
        revoke_session(session, "refresh_reuse_detected", commit=False)
        _add_revocation(payload, "refresh_reuse_detected")
        db.session.commit()
        current_app.logger.warning("Refresh token replay detected; affected session revoked")
        return None

    _add_revocation(payload, "refresh_rotated")
    new_refresh_jti = str(uuid4())
    session.refresh_jti = new_refresh_jti
    session.last_rotated_at = datetime.utcnow()
    session.expires_at = datetime.utcnow() + current_app.config["JWT_REFRESH_TOKEN_EXPIRES"]
    db.session.commit()
    return _token_pair(user_id, session_id, new_refresh_jti)


def revoke_session(session: AuthSession, reason: str, *, commit: bool = True) -> bool:
    changed = bool(session.is_active or session.revoked_at is None)
    session.is_active = False
    session.revoked_at = session.revoked_at or datetime.utcnow()
    session.revoked_reason = session.revoked_reason or reason
    if commit:
        db.session.commit()
    return changed


def revoke_session_from_access(payload: dict, reason: str = "logout") -> bool:
    session = AuthSession.query.filter_by(
        session_id=payload.get("sid"), user_id=payload.get("user_id")
    ).first()
    if not session:
        return False
    _add_revocation(payload, reason)
    changed = revoke_session(session, reason, commit=False)
    db.session.commit()
    return changed


def revoke_all_user_sessions(user_id: int, reason: str, *, commit: bool = True) -> int:
    sessions = AuthSession.query.filter_by(user_id=user_id, is_active=True).all()
    for session in sessions:
        revoke_session(session, reason, commit=False)
    if commit:
        db.session.commit()
    return len(sessions)


def cleanup_sessions(*, now: datetime | None = None, retention_days: int = 30, dry_run: bool = True) -> int:
    cutoff = (now or datetime.utcnow())
    retention_cutoff = cutoff.timestamp() - retention_days * 86400
    revoked_before = datetime.fromtimestamp(retention_cutoff)
    query = AuthSession.query.filter(
        (AuthSession.expires_at <= cutoff)
        | ((AuthSession.revoked_at.is_not(None)) & (AuthSession.revoked_at <= revoked_before))
    )
    count = query.count()
    if not dry_run and count:
        query.delete(synchronize_session=False)
        db.session.commit()
    return count
