"""Pinned ownership-census context for requests and database units of work."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from flask import g, has_request_context
from sqlalchemy import func, select, text
from sqlalchemy import event
from sqlalchemy.orm import Session

from backend.extensions import db
from backend.ownership_census import (
    CENSUS_PUBLISH_LOCK_KEY,
    OwnershipActiveCensus,
    OwnershipCensusScope,
)


_CONTEXT_KEY = "ownership_census_context"
_FENCED_TRANSACTION_KEY = "ownership_census_fenced_transaction"
_LOGICAL_CONTEXT_KEY = "ownership_census_logical_context"


@dataclass(frozen=True)
class CensusContext:
    """One immutable effective ownership census used by a logical unit of work."""

    census_id: str
    publication_order: int
    cache_version: int
    cache_token: str | int
    legacy: bool = False

    @property
    def token(self) -> tuple[int, str | int]:
        return self.cache_version, self.cache_token


class CensusUnavailable(RuntimeError):
    """The required active census is missing or incomplete."""


class CensusTransitioned(RuntimeError):
    """A later transaction tried to continue a logical unit on another census."""


def _actual_session(session):
    return session if hasattr(session, "get_transaction") else session()


def _request_context() -> CensusContext | None:
    if not has_request_context():
        return None
    return getattr(g, _CONTEXT_KEY, None)


def _legacy_context(epoch: int, count: int) -> CensusContext:
    return CensusContext(
        census_id="legacy-mt1c",
        publication_order=0,
        cache_version=int(epoch),
        cache_token=int(count),
        legacy=True,
    )


def _lock_and_resolve(session: Session) -> CensusContext:
    if session.get_bind().dialect.name == "postgresql":
        session.execute(
            text("SELECT pg_advisory_xact_lock_shared(:lock_key)"),
            {"lock_key": CENSUS_PUBLISH_LOCK_KEY},
            execution_options={"include_quarantined_for_certification": True},
        )
    # One snapshot query resolves canonical authority and the legacy fallback
    # token. This keeps the request fence affordable on uncensused v1.9.1 data.
    from backend.quarantine import (  # noqa: PLC0415
        OwnershipCertificationDecision,
        OwnershipCertificationScope,
    )

    active = OwnershipActiveCensus.__table__
    scope = OwnershipCensusScope.__table__
    row = session.execute(
        select(
            select(active.c.census_id)
            .where(active.c.singleton_id == 1)
            .scalar_subquery(),
            select(active.c.publication_order)
            .where(active.c.singleton_id == 1)
            .scalar_subquery(),
            select(active.c.cache_version)
            .where(active.c.singleton_id == 1)
            .scalar_subquery(),
            select(active.c.cache_token)
            .where(active.c.singleton_id == 1)
            .scalar_subquery(),
            select(func.count(scope.c.census_id)).scalar_subquery(),
            select(
                func.coalesce(func.max(OwnershipCertificationScope.decision_epoch), 0)
            ).scalar_subquery(),
            select(func.count(OwnershipCertificationDecision.id)).scalar_subquery(),
        ).execution_options(include_quarantined_for_certification=True)
    ).one()
    census_id, order, version, token, canonical_scope_count, epoch, count = row
    if census_id is not None:
        return CensusContext(
            census_id=str(census_id),
            publication_order=int(order),
            cache_version=int(version),
            cache_token=str(token),
        )
    if canonical_scope_count:
        raise CensusUnavailable("ownership census is unavailable")
    return _legacy_context(int(epoch), int(count))


def ensure_census_context(session: Session | None = None) -> CensusContext:
    """Fence the current transaction and return its immutable census snapshot."""

    session = _actual_session(session or db.session)
    expected = (
        _request_context()
        or session.info.get(_LOGICAL_CONTEXT_KEY)
        or session.info.get(_CONTEXT_KEY)
    )
    transaction = session.get_transaction()
    if (
        expected is not None
        and transaction is not None
        and session.info.get(_FENCED_TRANSACTION_KEY) is transaction
    ):
        return expected

    resolved = _lock_and_resolve(session)
    if expected is not None and resolved != expected:
        raise CensusTransitioned("ownership census changed; retry the unit of work")
    context = expected or resolved
    session.info[_CONTEXT_KEY] = context
    session.info[_FENCED_TRANSACTION_KEY] = session.get_transaction()
    if has_request_context() and _request_context() is None:
        setattr(g, _CONTEXT_KEY, context)
    return context


def clear_census_context(session: Session | None = None) -> None:
    session = _actual_session(session or db.session)
    session.info.pop(_CONTEXT_KEY, None)
    session.info.pop(_FENCED_TRANSACTION_KEY, None)
    session.info.pop(_LOGICAL_CONTEXT_KEY, None)
    if has_request_context() and hasattr(g, _CONTEXT_KEY):
        delattr(g, _CONTEXT_KEY)


@contextmanager
def census_unit_of_work(session: Session | None = None) -> Iterator[CensusContext]:
    """Explicit lifecycle for a background job or command census fence."""

    session = _actual_session(session or db.session)
    try:
        context = ensure_census_context(session)
        session.info[_LOGICAL_CONTEXT_KEY] = context
        yield context
    finally:
        clear_census_context(session)


@event.listens_for(Session, "after_transaction_end")
def _release_transaction_fence_marker(session: Session, transaction) -> None:
    if transaction.parent is None:
        session.info.pop(_FENCED_TRANSACTION_KEY, None)


@event.listens_for(Session, "after_soft_rollback")
def _clear_implicit_context_after_rollback(session: Session, _transaction) -> None:
    if not has_request_context() and _LOGICAL_CONTEXT_KEY not in session.info:
        session.info.pop(_CONTEXT_KEY, None)


__all__ = [
    "CensusContext",
    "CensusTransitioned",
    "CensusUnavailable",
    "census_unit_of_work",
    "clear_census_context",
    "ensure_census_context",
]
