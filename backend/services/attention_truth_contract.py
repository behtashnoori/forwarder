"""Opaque, presentation-safe parity contract for shared Attention truth.

Workspace and Control Tower keep their existing presentation and ordering
rules.  This module gives both read models one deterministic proof that a
displayed enrichment came from the same governed OIP fact, rank cohort and
freshness snapshot.  It deliberately discloses no database identifiers or
private evidence.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone


def _canonical_time(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def build_attention_truth_contract(
    *,
    shipment_public_id: str,
    situation_identity_key: str,
    policy_id: str,
    policy_version: str,
    source_watermark: str,
    calculated_at: str,
    urgency: str,
    severity: str,
    priority: str,
) -> dict:
    material = [
        "forwarder-attention-truth-v1",
        shipment_public_id,
        situation_identity_key,
        policy_id,
        policy_version,
        source_watermark,
    ]
    encoded = json.dumps(material, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return {
        "fingerprint": "sha256:" + hashlib.sha256(encoded).hexdigest(),
        "contract_version": "attention-truth-v1",
        "rank": {
            "policy_id": policy_id,
            "policy_version": policy_version,
            "urgency": urgency,
            "severity": severity,
            "priority": priority,
        },
        "freshness": {
            "status": "FRESH",
            "calculated_at": _canonical_time(calculated_at),
            "source_watermark": source_watermark,
        },
    }
