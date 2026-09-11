"""Create a deterministic, content-based fingerprint of a Git worktree."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable, Sequence


FORMAT_VERSION = 1
DOMAIN = b"forwarder-worktree-v1\0"


class FingerprintError(RuntimeError):
    """Raised when a trustworthy fingerprint cannot be produced."""


@dataclass(frozen=True)
class Entry:
    relative_path: str
    tracking_state: str
    size: int
    sha256: str
    content: bytes


def _run_git(root: Path, *arguments: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", "-C", os.fspath(root), *arguments],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise FingerprintError(f"could not execute Git: {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise FingerprintError(f"Git command failed ({completed.returncode}): {detail}")
    return completed.stdout


def resolve_repository_root(candidate: Path | None = None) -> Path:
    probe = (candidate or Path.cwd()).resolve(strict=True)
    output = _run_git(probe, "rev-parse", "--show-toplevel")
    try:
        value = output.rstrip(b"\r\n").decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise FingerprintError("repository root is not valid UTF-8") from exc
    if not value:
        raise FingerprintError("Git returned an empty repository root")
    root = Path(value).resolve(strict=True)
    if not root.is_dir():
        raise FingerprintError("resolved repository root is not a directory")
    return root


def _decode_git_paths(output: bytes) -> list[str]:
    raw_paths = output.split(b"\0")
    if raw_paths[-1:] == [b""]:
        raw_paths.pop()
    try:
        return [raw.decode("utf-8", errors="strict") for raw in raw_paths]
    except UnicodeDecodeError as exc:
        raise FingerprintError("Git returned a path that is not valid UTF-8") from exc


def _normalize_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    pure = PurePosixPath(normalized)
    if not normalized or pure.is_absolute() or ".." in pure.parts:
        raise FingerprintError(f"Git returned a non-relative path: {path!r}")
    if normalized != pure.as_posix() or normalized.startswith("./"):
        raise FingerprintError(f"Git returned a non-canonical path: {path!r}")
    return normalized


def _path_key(path: str) -> bytes:
    return path.encode("utf-8", errors="strict")


def collect_entries(root: Path) -> list[Entry]:
    selected = _decode_git_paths(
        _run_git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
    )
    tracked = {
        _normalize_path(path)
        for path in _decode_git_paths(_run_git(root, "ls-files", "--cached", "-z"))
    }

    normalized_paths: list[str] = []
    seen: set[str] = set()
    for raw_path in selected:
        path = _normalize_path(raw_path)
        if path in seen:
            raise FingerprintError(f"duplicate normalized path: {path}")
        seen.add(path)
        normalized_paths.append(path)

    entries: list[Entry] = []
    for relative_path in sorted(normalized_paths, key=_path_key):
        absolute_path = root.joinpath(*PurePosixPath(relative_path).parts)
        try:
            content = absolute_path.read_bytes()
        except OSError as exc:
            raise FingerprintError(f"could not read listed file {relative_path!r}: {exc}") from exc
        entries.append(
            Entry(
                relative_path=relative_path,
                tracking_state="tracked" if relative_path in tracked else "untracked",
                size=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
                content=content,
            )
        )
    return entries


def fingerprint_entries(entries: Iterable[Entry]) -> str:
    ordered = sorted(entries, key=lambda entry: _path_key(entry.relative_path))
    seen: set[str] = set()
    digest = hashlib.sha256()
    digest.update(DOMAIN)
    for entry in ordered:
        path = _normalize_path(entry.relative_path)
        if path in seen:
            raise FingerprintError(f"duplicate normalized path: {path}")
        seen.add(path)
        path_bytes = _path_key(path)
        digest.update(path_bytes)
        digest.update(b"\0")
        digest.update(struct.pack("<Q", len(entry.content)))
        digest.update(entry.content)
    return digest.hexdigest()


def build_result(root: Path, entries: Sequence[Entry]) -> dict[str, object]:
    tracked_count = sum(entry.tracking_state == "tracked" for entry in entries)
    return {
        "format_version": FORMAT_VERSION,
        "fingerprint": fingerprint_entries(entries),
        "entry_count": len(entries),
        "tracked_count": tracked_count,
        "untracked_count": len(entries) - tracked_count,
        "path_source": "git ls-files --cached --others --exclude-standard -z",
        "path_ordering": "normalized UTF-8 bytes, ascending",
        "repository_root": os.fspath(root),
    }


def _manifest(result: dict[str, object], entries: Sequence[Entry]) -> dict[str, object]:
    ordered = sorted(entries, key=lambda entry: _path_key(entry.relative_path))
    return {
        **result,
        "entries": [
            {
                "relative_path": entry.relative_path,
                "tracking_state": entry.tracking_state,
                "size": entry.size,
                "sha256": entry.sha256,
            }
            for entry in ordered
        ],
    }


def _manifest_target_allowed(root: Path, target: Path) -> bool:
    try:
        relative = target.resolve(strict=False).relative_to(root)
    except ValueError:
        return True
    completed = subprocess.run(
        ["git", "-C", os.fspath(root), "check-ignore", "--quiet", "--", relative.as_posix()],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    if completed.returncode not in (0, 1):
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise FingerprintError(f"could not validate manifest exclusion: {detail}")
    return completed.returncode == 0


def write_manifest(
    root: Path, target: Path, result: dict[str, object], entries: Sequence[Entry]
) -> None:
    target = target.resolve(strict=False)
    if not _manifest_target_allowed(root, target):
        raise FingerprintError(
            "manifest target is inside the repository and is not Git-ignored"
        )
    payload = json.dumps(
        _manifest(result, entries), ensure_ascii=False, indent=2, sort_keys=False
    ) + "\n"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
        temporary.write_text(payload, encoding="utf-8", newline="\n")
        os.replace(temporary, target)
    except OSError as exc:
        raise FingerprintError(f"could not write manifest {target}: {exc}") from exc


def _virtual_entry(path: str, content: bytes) -> Entry:
    return Entry(path, "untracked", len(content), hashlib.sha256(content).hexdigest(), content)


def run_self_test() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="forwarder-worktree-fingerprint-") as directory:
        fixture = Path(directory)
        first = fixture / "a.txt"
        second = fixture / "B.txt"
        first.write_bytes(b"alpha\n")
        second.write_bytes(b"beta\0")

        base_entries = [_virtual_entry("a.txt", first.read_bytes()), _virtual_entry("B.txt", second.read_bytes())]
        base = fingerprint_entries(base_entries)
        enumeration = fingerprint_entries(list(reversed(base_entries)))
        os.utime(first, (1_000_000_000, 1_000_000_000))
        mtime = fingerprint_entries([_virtual_entry("a.txt", first.read_bytes()), base_entries[1]])
        byte_change = fingerprint_entries([_virtual_entry("a.txt", b"Alpha\n"), base_entries[1]])
        rename = fingerprint_entries([base_entries[0], _virtual_entry("C.txt", second.read_bytes())])
        same_count = fingerprint_entries([base_entries[0], _virtual_entry("D.txt", second.read_bytes())])
        case_distinct = fingerprint_entries(
            [_virtual_entry("case.txt", b"one"), _virtual_entry("Case.txt", b"two")]
        )
        case_folded = fingerprint_entries([_virtual_entry("case.txt", b"two")])

    checks = {
        "enumeration_order_independent": base == enumeration,
        "mtime_independent": base == mtime,
        "one_byte_change_detected": base != byte_change,
        "rename_detected": base != rename,
        "same_count_remove_add_detected": base != same_count,
        "case_distinct_identity_preserved": case_distinct != case_folded,
    }
    return {"self_test": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, help="path inside the target Git repository")
    parser.add_argument("--manifest", type=Path, help="optional external or Git-ignored manifest path")
    parser.add_argument("--self-test", action="store_true", help="run deterministic algorithm checks")
    args = parser.parse_args()

    try:
        if args.self_test:
            result = run_self_test()
            print(json.dumps(result, sort_keys=True))
            return 0 if result["self_test"] == "PASS" else 1
        root = resolve_repository_root(args.repo)
        entries = collect_entries(root)
        result = build_result(root, entries)
        if args.manifest:
            write_manifest(root, args.manifest, result, entries)
            result["manifest"] = os.fspath(args.manifest.resolve(strict=False))
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (FingerprintError, OSError, ValueError) as exc:
        print(f"worktree fingerprint failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
