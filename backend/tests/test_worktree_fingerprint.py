from __future__ import annotations

import json

import pytest

from scripts.worktree_fingerprint import (
    Entry,
    FingerprintError,
    build_result,
    fingerprint_entries,
    run_self_test,
    write_manifest,
)


def _entry(path: str, content: bytes, state: str = "tracked") -> Entry:
    import hashlib

    return Entry(path, state, len(content), hashlib.sha256(content).hexdigest(), content)


def test_fingerprint_is_bytewise_ordered_and_metadata_independent() -> None:
    lower = _entry("backend/a.py", b"alpha")
    upper = _entry("README.md", b"beta")

    assert fingerprint_entries([lower, upper]) == fingerprint_entries([upper, lower])
    assert run_self_test()["self_test"] == "PASS"


def test_fingerprint_detects_content_path_and_same_count_changes() -> None:
    baseline = fingerprint_entries([_entry("a", b"one"), _entry("b", b"two")])

    assert baseline != fingerprint_entries([_entry("a", b"One"), _entry("b", b"two")])
    assert baseline != fingerprint_entries([_entry("a", b"one"), _entry("c", b"two")])


def test_fingerprint_rejects_duplicate_or_non_relative_paths() -> None:
    with pytest.raises(FingerprintError, match="duplicate normalized path"):
        fingerprint_entries([_entry("same", b"one"), _entry("same", b"two")])
    with pytest.raises(FingerprintError, match="non-relative path"):
        fingerprint_entries([_entry("../outside", b"one")])


def test_external_manifest_is_deterministic(tmp_path) -> None:
    root = tmp_path / "repository"
    root.mkdir()
    entries = [_entry("a", b"one"), _entry("B", b"two", "untracked")]
    result = build_result(root, entries)
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    write_manifest(root, first, result, entries)
    write_manifest(root, second, result, entries)

    assert first.read_bytes() == second.read_bytes()
    manifest = json.loads(first.read_text(encoding="utf-8"))
    assert [entry["relative_path"] for entry in manifest["entries"]] == ["B", "a"]
    assert manifest["fingerprint"] == result["fingerprint"]
