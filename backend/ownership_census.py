"""Append-only ownership decisions and atomic active-census publication."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import hmac
import json
import os
import re
from typing import Callable, Mapping, Sequence
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index, UniqueConstraint, event, func, inspect, select, text
from sqlalchemy.orm import Session

from backend.extensions import db
from backend.resource_identity import ResourceIdentity, scalar_identity


CLASSIFICATIONS = frozenset(
    {"DETERMINISTIC", "CONFLICT", "UNRESOLVED", "INVALID_LINEAGE"}
)
ENFORCEMENT_STATES = frozenset({"CLEAR", "QUARANTINED"})
_SHA256 = re.compile(r"[0-9a-f]{64}")
_PUBLISH_LOCK_KEY = 0x4D543144  # ASCII "MT1D"; transaction-scoped in PostgreSQL.


class CensusPublicationError(RuntimeError):
    """Base class for rejected census publication."""


class UnauthorizedCensusPublisher(CensusPublicationError):
    """Raised when normal request code attempts to invoke the publisher."""


class StaleCensusPublication(CensusPublicationError):
    """Raised when a publication does not extend the active census."""


class CensusIntegrityError(CensusPublicationError):
    """Raised when a census is partial, malformed, or internally inconsistent."""


class _PublisherAuthority:
    __slots__ = ("_proof", "database_roles")

    def __init__(self, proof, database_roles: frozenset[str]) -> None:
        self._proof = proof
        self.database_roles = database_roles


_AUTHORITY_PROOF = object()


def internal_publisher_authority(token: str) -> _PublisherAuthority:
    """Return the capability reserved for internal CLI/administrative wiring.

    This module is deliberately not imported by any request route.  Keeping the
    capability explicit makes accidental publication from normal services
    reviewable and testable; infrastructure must additionally restrict the DB
    role used by the internal publisher.
    """

    configured = os.getenv("MT1D_CENSUS_PUBLISHER_TOKEN", "")
    roles = frozenset(
        item.strip()
        for item in os.getenv("MT1D_CENSUS_PUBLISHER_DATABASE_ROLES", "").split(",")
        if item.strip()
    )
    if (
        len(configured) < 32
        or not isinstance(token, str)
        or not hmac.compare_digest(token, configured)
        or not roles
    ):
        raise UnauthorizedCensusPublisher("internal publisher authorization denied")
    return _PublisherAuthority(_AUTHORITY_PROOF, roles)


BIGINT = db.BigInteger().with_variant(db.Integer, "sqlite")


class OwnershipCensus(db.Model):
    __tablename__ = "ownership_census"
    census_id = db.Column(db.String(64), primary_key=True)
    analysis_version = db.Column(db.String(64), nullable=False)
    publication_order = db.Column(db.BigInteger, nullable=False, unique=True)
    manifest_fingerprint = db.Column(db.String(64), nullable=False, unique=True)
    source_fingerprint = db.Column(db.String(64), nullable=False)
    previous_census_id = db.Column(
        db.String(64), db.ForeignKey("ownership_census.census_id"), nullable=True
    )
    publisher = db.Column(db.String(128), nullable=False)
    published_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (
        UniqueConstraint(
            "census_id", "publication_order", name="uq_ownership_census_id_order"
        ),
        CheckConstraint("publication_order >= 1", name="ck_ownership_census_order"),
        CheckConstraint(
            "length(manifest_fingerprint) = 64",
            name="ck_ownership_census_manifest_fingerprint",
        ),
        CheckConstraint(
            "length(source_fingerprint) = 64",
            name="ck_ownership_census_source_fingerprint",
        ),
    )


class OwnershipCensusScope(db.Model):
    __tablename__ = "ownership_census_scope"
    census_id = db.Column(
        db.String(64), db.ForeignKey("ownership_census.census_id"), primary_key=True
    )
    resource_type = db.Column(db.String(80), primary_key=True)
    expected_decision_count = db.Column(db.BigInteger, nullable=False)
    evidence_fingerprint = db.Column(db.String(64), nullable=False)
    __table_args__ = (
        CheckConstraint(
            "expected_decision_count >= 0", name="ck_ownership_census_scope_count"
        ),
        CheckConstraint(
            "length(evidence_fingerprint) = 64",
            name="ck_ownership_census_scope_fingerprint",
        ),
    )


class OwnershipDecision(db.Model):
    __tablename__ = "ownership_decision"
    id = db.Column(BIGINT, primary_key=True)
    census_id = db.Column(
        db.String(64), db.ForeignKey("ownership_census.census_id"), nullable=False
    )
    resource_type = db.Column(db.String(80), nullable=False)
    resource_key_hash = db.Column(db.String(64), nullable=False)
    resource_key_payload = db.Column(db.Text, nullable=False)
    scalar_integer_id = db.Column(db.BigInteger, nullable=True)
    decision_version = db.Column(db.BigInteger, nullable=False)
    classification = db.Column(db.String(32), nullable=False)
    enforcement_state = db.Column(db.String(16), nullable=False)
    source_fingerprint = db.Column(db.String(64), nullable=False)
    effective_order = db.Column(db.BigInteger, nullable=False)
    effective_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    supersedes_decision_id = db.Column(
        BIGINT, db.ForeignKey("ownership_decision.id"), nullable=True
    )
    root_resource_type = db.Column(db.String(80), nullable=False)
    root_resource_key_hash = db.Column(db.String(64), nullable=False)
    root_resource_key_payload = db.Column(db.Text, nullable=False)
    __table_args__ = (
        UniqueConstraint(
            "census_id",
            "resource_type",
            "resource_key_hash",
            name="uq_ownership_decision_census_resource",
        ),
        UniqueConstraint(
            "resource_type",
            "resource_key_hash",
            "decision_version",
            name="uq_ownership_decision_resource_version",
        ),
        Index(
            "ix_ownership_decision_active_scalar",
            "census_id",
            "resource_type",
            "scalar_integer_id",
        ),
        Index(
            "ix_ownership_decision_active_key",
            "census_id",
            "resource_type",
            "resource_key_hash",
        ),
        CheckConstraint("decision_version >= 1", name="ck_ownership_decision_version"),
        CheckConstraint("effective_order >= 1", name="ck_ownership_decision_order"),
        CheckConstraint(
            "classification IN ('DETERMINISTIC','CONFLICT','UNRESOLVED','INVALID_LINEAGE')",
            name="ck_ownership_decision_classification_v2",
        ),
        CheckConstraint(
            "enforcement_state IN ('CLEAR','QUARANTINED')",
            name="ck_ownership_decision_enforcement",
        ),
        CheckConstraint(
            "enforcement_state <> 'CLEAR' OR classification = 'DETERMINISTIC'",
            name="ck_ownership_decision_clear_deterministic",
        ),
        CheckConstraint(
            "length(resource_key_hash) = 64 AND length(root_resource_key_hash) = 64 "
            "AND length(source_fingerprint) = 64",
            name="ck_ownership_decision_hash_lengths",
        ),
    )


class OwnershipActiveCensus(db.Model):
    __tablename__ = "ownership_active_census"
    singleton_id = db.Column(db.Integer, primary_key=True)
    census_id = db.Column(
        db.String(64), db.ForeignKey("ownership_census.census_id"), nullable=False, unique=True
    )
    publication_order = db.Column(db.BigInteger, nullable=False)
    cache_version = db.Column(db.BigInteger, nullable=False)
    cache_token = db.Column(db.String(36), nullable=False, unique=True)
    activated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (
        CheckConstraint("singleton_id = 1", name="ck_ownership_active_singleton"),
        CheckConstraint("publication_order >= 1", name="ck_ownership_active_order"),
        CheckConstraint("cache_version >= 1", name="ck_ownership_active_cache_version"),
        ForeignKeyConstraint(
            ["census_id", "publication_order"],
            ["ownership_census.census_id", "ownership_census.publication_order"],
            name="fk_ownership_active_census_order",
        ),
    )


class OwnershipCensusActivation(db.Model):
    __tablename__ = "ownership_census_activation"
    id = db.Column(BIGINT, primary_key=True)
    census_id = db.Column(
        db.String(64), db.ForeignKey("ownership_census.census_id"), nullable=False, unique=True
    )
    previous_census_id = db.Column(
        db.String(64), db.ForeignKey("ownership_census.census_id"), nullable=True
    )
    cache_version = db.Column(db.BigInteger, nullable=False, unique=True)
    cache_token = db.Column(db.String(36), nullable=False, unique=True)
    activated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


@dataclass(frozen=True)
class CensusDecisionInput:
    identity: ResourceIdentity
    classification: str
    enforcement_state: str
    source_fingerprint: str
    root_identity: ResourceIdentity | None = None
    effective_order: int = 1


@dataclass(frozen=True)
class CensusPublication:
    census_id: str
    analysis_version: str
    publication_order: int
    previous_census_id: str | None
    source_fingerprint: str
    publisher: str
    decisions: Sequence[CensusDecisionInput]
    scope_counts: Mapping[str, int]
    scope_fingerprints: Mapping[str, str]


@dataclass(frozen=True)
class PublicationResult:
    census_id: str
    publication_order: int
    cache_version: int
    cache_token: str
    replayed: bool


def _valid_sha256(value: str) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _manifest(publication: CensusPublication) -> str:
    decisions = [
        {
            "classification": item.classification,
            "effective_order": item.effective_order,
            "enforcement_state": item.enforcement_state,
            "identity": item.identity.as_json(),
            "root_identity": (item.root_identity or item.identity).as_json(),
            "source_fingerprint": item.source_fingerprint,
        }
        for item in publication.decisions
    ]
    decisions.sort(key=lambda item: (
        item["identity"]["resource_type"], item["identity"]["resource_key_hash"]
    ))
    value = {
        "analysis_version": publication.analysis_version,
        "census_id": publication.census_id,
        "decisions": decisions,
        "previous_census_id": publication.previous_census_id,
        "publication_order": publication.publication_order,
        "publisher": publication.publisher,
        "scope_counts": dict(sorted(publication.scope_counts.items())),
        "scope_fingerprints": dict(sorted(publication.scope_fingerprints.items())),
        "source_fingerprint": publication.source_fingerprint,
    }
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return sha256(encoded.encode("utf-8")).hexdigest()


def _validate(publication: CensusPublication) -> str:
    if (
        not publication.census_id
        or len(publication.census_id) > 64
        or not publication.analysis_version
        or len(publication.analysis_version) > 64
        or publication.publication_order < 1
        or not publication.publisher
        or len(publication.publisher) > 128
        or not _valid_sha256(publication.source_fingerprint)
    ):
        raise CensusIntegrityError("invalid census publication metadata")
    if set(publication.scope_counts) != set(publication.scope_fingerprints):
        raise CensusIntegrityError("scope counts and fingerprints do not match")
    if any(count < 0 for count in publication.scope_counts.values()) or any(
        not _valid_sha256(value) for value in publication.scope_fingerprints.values()
    ):
        raise CensusIntegrityError("invalid census scope metadata")

    identities: dict[tuple[str, str], ResourceIdentity] = {}
    counts = {resource_type: 0 for resource_type in publication.scope_counts}
    for item in publication.decisions:
        identity = item.identity
        key = (identity.resource_type, identity.key_hash)
        previous = identities.get(key)
        if previous is not None:
            if previous.key_payload != identity.key_payload:
                raise CensusIntegrityError("resource identity hash collision")
            raise CensusIntegrityError("duplicate resource decision")
        identities[key] = identity
        if identity.resource_type not in counts:
            raise CensusIntegrityError("decision is outside the declared census scope")
        counts[identity.resource_type] += 1
        if item.classification not in CLASSIFICATIONS:
            raise CensusIntegrityError("unknown ownership classification")
        if item.enforcement_state not in ENFORCEMENT_STATES:
            raise CensusIntegrityError("unknown enforcement state")
        if item.enforcement_state == "CLEAR" and item.classification != "DETERMINISTIC":
            raise CensusIntegrityError("non-deterministic ownership must fail closed")
        if not _valid_sha256(item.source_fingerprint) or item.effective_order < 1:
            raise CensusIntegrityError("invalid decision provenance")

    if counts != dict(publication.scope_counts):
        raise CensusIntegrityError("census decision cardinality is incomplete")
    for item in publication.decisions:
        root = item.root_identity or item.identity
        if (root.resource_type, root.key_hash) not in identities:
            raise CensusIntegrityError("lineage root is absent from the census")
    return _manifest(publication)


def _lock_publisher(session: Session) -> None:
    if session.get_bind().dialect.name == "postgresql":
        session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": _PUBLISH_LOCK_KEY},
        )


_EXPLICIT_ROOT_TYPES = frozenset(
    {
        "AssignmentRule",
        "Customer",
        "CustomerGamification",
        "Project",
        "ReferralAutoAssignState",
        "ReferralRule",
        "Report",
        "ShipmentRequest",
    }
)


def _table_for_resource_type(resource_type: str):
    for mapper in db.Model.registry.mappers:
        if mapper.class_.__name__ == resource_type:
            return mapper.local_table
    return db.metadata.tables.get(resource_type)


def _identity_row(session: Session, identity: ResourceIdentity):
    table = _table_for_resource_type(identity.resource_type)
    if table is None:
        return None, None
    primary_keys = tuple(table.primary_key.columns)
    expected_names = [column.name for column in primary_keys]
    components = list(identity.components)
    if [item.name for item in components] != expected_names:
        raise CensusIntegrityError("identity does not match the resource primary key")
    predicates = []
    for column, item in zip(primary_keys, components):
        try:
            python_type = column.type.python_type
        except NotImplementedError:
            python_type = str
        expected_kind = (
            "INTEGER"
            if python_type is int
            else "UUID"
            if python_type is UUID
            else "STRING"
        )
        if item.kind != expected_kind:
            raise CensusIntegrityError("identity kind does not match the resource primary key")
        value = (
            int(item.value)
            if item.kind == "INTEGER"
            else UUID(item.value)
            if item.kind == "UUID"
            else item.value
        )
        predicates.append(column == value)
    row = session.execute(
        select(table)
        .where(*predicates)
        .execution_options(include_quarantined_for_certification=True)
    ).mappings().one_or_none()
    if row is None:
        raise CensusIntegrityError("census decision references a missing resource")
    return table, row


def _can_be_lineage_root(resource_type: str, table) -> bool:
    if resource_type in _EXPLICIT_ROOT_TYPES:
        return True
    organization = table.c.get("organization_id") if table is not None else None
    return organization is not None and not organization.nullable


def _root_is_reachable(
    session: Session,
    identity: ResourceIdentity,
    desired_root: ResourceIdentity,
    *,
    visited: set[tuple[str, str]],
) -> bool:
    key = (identity.resource_type, identity.key_hash)
    if key in visited:
        return False
    visited.add(key)
    table, row = _identity_row(session, identity)
    if table is None:
        return identity == desired_root
    if identity == desired_root and _can_be_lineage_root(identity.resource_type, table):
        return True

    # Imported lazily because quarantine owns the legacy domain graph and also
    # imports these census models during application initialization.
    from backend.quarantine import PARENT_REFERENCES

    for attribute, parent_type in PARENT_REFERENCES.get(identity.resource_type, ()):
        parent_id = row.get(attribute)
        if parent_id is None:
            continue
        parent = scalar_identity(parent_type, parent_id)
        if _root_is_reachable(
            session, parent, desired_root, visited=set(visited)
        ):
            return True
    return False


def _parent_identities(identity: ResourceIdentity, row) -> tuple[ResourceIdentity, ...]:
    from backend.quarantine import PARENT_REFERENCES

    return tuple(
        scalar_identity(parent_type, row[attribute])
        for attribute, parent_type in PARENT_REFERENCES.get(
            identity.resource_type, ()
        )
        if row.get(attribute) is not None
    )


def _input_is_effectively_clear(
    item: CensusDecisionInput,
    decisions: Mapping[tuple[str, str], CensusDecisionInput],
) -> bool:
    if item.enforcement_state != "CLEAR":
        return False
    root = item.root_identity or item.identity
    root_item = decisions.get((root.resource_type, root.key_hash))
    return root_item is not None and root_item.enforcement_state == "CLEAR"


def _validate_database_census(session: Session, publication: CensusPublication) -> None:
    decisions = {
        (item.identity.resource_type, item.identity.key_hash): item
        for item in publication.decisions
    }
    for resource_type, expected_count in publication.scope_counts.items():
        table = _table_for_resource_type(resource_type)
        if table is None:
            continue
        actual_count = session.execute(
            select(func.count())
            .select_from(table)
            .execution_options(include_quarantined_for_certification=True)
        ).scalar_one()
        if int(actual_count) != expected_count:
            raise CensusIntegrityError("census scope does not cover every database row")
    for item in publication.decisions:
        table, row = _identity_row(session, item.identity)
        if table is None:
            continue
        root = item.root_identity or item.identity
        if (root.resource_type, root.key_hash) not in decisions:
            raise CensusIntegrityError("lineage root has no decision")
        if not _root_is_reachable(session, item.identity, root, visited=set()):
            raise CensusIntegrityError(
                "declared lineage root does not match database lineage: "
                f"{item.identity.resource_type}->{root.resource_type}"
            )
        if item.enforcement_state == "CLEAR":
            for parent in _parent_identities(item.identity, row):
                parent_item = decisions.get((parent.resource_type, parent.key_hash))
                parent_is_declared_root = parent == root
                if parent_item is None or (
                    not parent_is_declared_root
                    and not _input_is_effectively_clear(parent_item, decisions)
                ):
                    raise CensusIntegrityError(
                        "clear resource has a missing or quarantined parent decision"
                    )


def publish_census(
    session: Session,
    publication: CensusPublication,
    *,
    authority: _PublisherAuthority,
    failure_hook: Callable[[], None] | None = None,
) -> PublicationResult:
    """Validate, append and activate one complete census in one transaction."""

    if not isinstance(authority, _PublisherAuthority) or authority._proof is not _AUTHORITY_PROOF:
        raise UnauthorizedCensusPublisher("census publication requires internal authority")
    manifest = _validate(publication)
    if session.in_transaction():
        raise CensusPublicationError("publisher requires a clean transaction boundary")

    with session.begin():
        _lock_publisher(session)
        database_role = (
            session.execute(text("SELECT current_user")).scalar_one()
            if session.get_bind().dialect.name == "postgresql"
            else "sqlite"
        )
        if database_role not in authority.database_roles:
            raise UnauthorizedCensusPublisher("database role is not authorized to publish")
        active = session.execute(
            select(OwnershipActiveCensus)
            .where(OwnershipActiveCensus.singleton_id == 1)
            .with_for_update()
        ).scalar_one_or_none()
        existing = session.get(OwnershipCensus, publication.census_id)
        if existing is not None:
            if existing.manifest_fingerprint != manifest:
                raise CensusIntegrityError("census ID was already used for different content")
            if active is None or active.census_id != existing.census_id:
                raise StaleCensusPublication("historical census cannot be reactivated")
            return PublicationResult(
                active.census_id,
                active.publication_order,
                active.cache_version,
                active.cache_token,
                True,
            )

        active_id = active.census_id if active is not None else None
        active_order = active.publication_order if active is not None else 0
        if publication.previous_census_id != active_id:
            raise StaleCensusPublication("publication does not extend the active census")
        if publication.publication_order <= active_order:
            raise StaleCensusPublication("publication order is stale")
        if active is not None:
            previous_scope = set(session.execute(
                select(OwnershipCensusScope.resource_type).where(
                    OwnershipCensusScope.census_id == active.census_id
                )
            ).scalars())
            if not previous_scope.issubset(publication.scope_counts):
                raise CensusIntegrityError("publication cannot drop an active census scope")
        _validate_database_census(session, publication)

        census = OwnershipCensus(
            census_id=publication.census_id,
            analysis_version=publication.analysis_version,
            publication_order=publication.publication_order,
            manifest_fingerprint=manifest,
            source_fingerprint=publication.source_fingerprint,
            previous_census_id=publication.previous_census_id,
            publisher=publication.publisher,
        )
        session.add(census)
        for resource_type, count in publication.scope_counts.items():
            session.add(OwnershipCensusScope(
                census_id=publication.census_id,
                resource_type=resource_type,
                expected_decision_count=count,
                evidence_fingerprint=publication.scope_fingerprints[resource_type],
            ))

        prior: dict[tuple[str, str], OwnershipDecision] = {}
        keys = {(item.identity.resource_type, item.identity.key_hash) for item in publication.decisions}
        if keys:
            # Supersede the latest historical decision even when an identity
            # was absent from the immediately preceding census. Versions must
            # never restart or collide after delete/recreate lifecycles.
            for row in session.execute(
                select(OwnershipDecision).order_by(
                    OwnershipDecision.decision_version.desc()
                )
            ).scalars():
                key = (row.resource_type, row.resource_key_hash)
                if key in keys and key not in prior:
                    prior[key] = row

        for item in publication.decisions:
            identity = item.identity
            root = item.root_identity or identity
            previous = prior.get((identity.resource_type, identity.key_hash))
            if previous is not None and previous.resource_key_payload != identity.key_payload:
                raise CensusIntegrityError("stored identity hash collision")
            session.add(OwnershipDecision(
                census_id=publication.census_id,
                resource_type=identity.resource_type,
                resource_key_hash=identity.key_hash,
                resource_key_payload=identity.key_payload,
                scalar_integer_id=identity.scalar_integer,
                decision_version=(previous.decision_version + 1) if previous else 1,
                classification=item.classification,
                enforcement_state=item.enforcement_state,
                source_fingerprint=item.source_fingerprint,
                effective_order=item.effective_order,
                supersedes_decision_id=previous.id if previous else None,
                root_resource_type=root.resource_type,
                root_resource_key_hash=root.key_hash,
                root_resource_key_payload=root.key_payload,
            ))
        session.flush()
        if failure_hook is not None:
            failure_hook()

        cache_version = (active.cache_version + 1) if active is not None else 1
        cache_token = str(uuid4())
        session.add(OwnershipCensusActivation(
            census_id=publication.census_id,
            previous_census_id=active_id,
            cache_version=cache_version,
            cache_token=cache_token,
        ))
        if active is None:
            session.add(OwnershipActiveCensus(
                singleton_id=1,
                census_id=publication.census_id,
                publication_order=publication.publication_order,
                cache_version=cache_version,
                cache_token=cache_token,
            ))
        else:
            active.census_id = publication.census_id
            active.publication_order = publication.publication_order
            active.cache_version = cache_version
            active.cache_token = cache_token
            active.activated_at = datetime.utcnow()
    session.expire_all()
    return PublicationResult(
        publication.census_id,
        publication.publication_order,
        cache_version,
        cache_token,
        False,
    )


@event.listens_for(Session, "before_flush")
def _prevent_history_rewrite(session: Session, _context, _instances) -> None:
    immutable = (OwnershipCensus, OwnershipCensusScope, OwnershipDecision, OwnershipCensusActivation)
    if any(isinstance(row, immutable) for row in session.dirty.union(session.deleted)):
        raise CensusIntegrityError("ownership census history is append-only")
    for row in session.dirty:
        if isinstance(row, OwnershipActiveCensus):
            state = inspect(row)
            version_history = state.attrs.cache_version.history
            token_history = state.attrs.cache_token.history
            census_history = state.attrs.census_id.history
            if not (
                version_history.deleted
                and version_history.added
                and version_history.added[0] == version_history.deleted[0] + 1
                and token_history.deleted
                and token_history.added
                and token_history.added[0] != token_history.deleted[0]
                and census_history.deleted
                and census_history.added
                and census_history.added[0] != census_history.deleted[0]
            ):
                raise CensusIntegrityError("active census transition must rotate version and token")
    if any(isinstance(row, OwnershipActiveCensus) for row in session.deleted):
        raise CensusIntegrityError("active census authority cannot be deleted")


__all__ = [
    "CLASSIFICATIONS",
    "ENFORCEMENT_STATES",
    "CensusDecisionInput",
    "CensusIntegrityError",
    "CensusPublication",
    "CensusPublicationError",
    "OwnershipActiveCensus",
    "OwnershipCensus",
    "OwnershipCensusActivation",
    "OwnershipCensusScope",
    "OwnershipDecision",
    "PublicationResult",
    "StaleCensusPublication",
    "UnauthorizedCensusPublisher",
    "internal_publisher_authority",
    "publish_census",
]
