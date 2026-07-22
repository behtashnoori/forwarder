"""Redacted secret scanner for the tracked tree or reachable Git history."""
from __future__ import annotations

import argparse
import hashlib
import io
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
URL_PATTERN = re.compile(
    rb"(?:postgres(?:ql)?(?:\+[a-z0-9_]+)?|mysql(?:\+[a-z0-9_]+)?|mongodb(?:\+srv)?)"
    rb"://([^\s:/]+):([^\s@/]+)@([^\s/]+)/(\S+)",
    re.IGNORECASE,
)
TOKEN_PATTERNS = (
    ("private-key", re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("aws-access-key", re.compile(rb"\bAKIA[0-9A-Z]{16}\b")),
    ("github-token", re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("named-secret", re.compile(
        rb"(?i)(?:password|secret_key|jwt_secret_key)\s*[:=]\s*['\"]([^'\"\r\n]{8,})['\"]"
    )),
)
PLACEHOLDERS = {b"change_me", b"password", b"<password>", b"example", b"test"}
# Reviewed legacy development/example values. Store only non-reversible hashes;
# production credentials are never eligible for this baseline.
REVIEWED_NON_PRODUCTION_FINGERPRINTS = {
    "fef372b9e8", "9ec2d5694a", "34a6c1a960",
    "bd4b969ec2", "0907ae7f66", "240be518fa",
}


def git(*args: str, input_data: bytes | None = None) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=ROOT, input=input_data, check=True, capture_output=True
    ).stdout


def findings(data: bytes, path: str = "") -> list[tuple[int, str, str]]:
    result = []
    for match in URL_PATTERN.finditer(data):
        password = match.group(2).lower()
        database = match.group(4).lower().rstrip(b"\"'`,;)")
        if password in PLACEHOLDERS or b"<" in password or b"test" in database:
            continue
        line = data.count(b"\n", 0, match.start()) + 1
        fingerprint = hashlib.sha256(match.group(0)).hexdigest()[:10]
        result.append((line, fingerprint, "credential-url"))
    test_context = "/tests/" in f"/{path.replace(chr(92), '/')}" or "test" in Path(path).name.lower()
    if not test_context:
        for secret_type, pattern in TOKEN_PATTERNS:
            for match in pattern.finditer(data):
                candidate = match.group(1) if match.lastindex else match.group(0)
                lowered = candidate.lower()
                if any(marker in lowered for marker in PLACEHOLDERS):
                    continue
                line = data.count(b"\n", 0, match.start()) + 1
                fingerprint = hashlib.sha256(candidate).hexdigest()[:10]
                if fingerprint in REVIEWED_NON_PRODUCTION_FINGERPRINTS:
                    continue
                result.append((line, fingerprint, secret_type))
    return result


def scan_current() -> int:
    found = 0
    for raw_path in git(
        "ls-files", "-z", "--cached", "--others", "--exclude-standard"
    ).split(b"\0"):
        if not raw_path:
            continue
        path = ROOT / raw_path.decode("utf-8", "surrogateescape")
        try:
            data = path.read_bytes()
        except (OSError, ValueError):
            continue
        for line, fingerprint, secret_type in findings(data, str(path.relative_to(ROOT))):
            found += 1
            print(f"path={path.relative_to(ROOT)} line={line} type={secret_type} "
                  f"status=redacted fingerprint={fingerprint}")
    print(f"scan=current-tree findings={found} redaction=enabled")
    return 1 if found else 0


def iter_batch_blobs(
    batch: bytes, objects: dict[str, set[str]]
) -> list[tuple[str, set[str], bytes]]:
    """Parse cat-file batch output while consuming every object's payload."""
    blobs = []
    stream = io.BytesIO(batch)
    for requested_oid, paths in objects.items():
        header = stream.readline().decode("ascii", "replace").strip().split()
        if len(header) < 3:
            raise RuntimeError(f"Malformed cat-file header for {requested_oid[:10]}")
        oid, object_type, raw_size = header[:3]
        size = int(raw_size)
        data = stream.read(size)
        delimiter = stream.read(1)
        if len(data) != size or delimiter != b"\n":
            raise RuntimeError(f"Truncated cat-file payload for {requested_oid[:10]}")
        if object_type == "blob":
            blobs.append((oid, paths, data))
    return blobs


def scan_history() -> int:
    objects: dict[str, set[str]] = {}
    for row in git("rev-list", "--objects", "--all").decode("utf-8", "replace").splitlines():
        oid, _, path = row.partition(" ")
        if path:
            objects.setdefault(oid, set()).add(path)

    found = 0
    batch = subprocess.run(
        ["git", "cat-file", "--batch"], cwd=ROOT,
        input="".join(f"{oid}\n" for oid in objects).encode(),
        check=True, capture_output=True,
    ).stdout
    for oid, paths, data in iter_batch_blobs(batch, objects):
        safe_path = sorted(paths)[0]
        matches = findings(data, safe_path)
        for line, fingerprint, secret_type in matches:
            found += 1
            print(f"object={oid[:10]} path={safe_path} line={line} type={secret_type} "
                  f"status=redacted fingerprint={fingerprint} reachable=yes "
                  "first_seen=see-incident-report last_seen=see-incident-report")
    print(f"scan=reachable-history findings={found} redaction=enabled")
    return 3 if found else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scope", choices=("current", "history"))
    args = parser.parse_args()
    return scan_current() if args.scope == "current" else scan_history()


if __name__ == "__main__":
    raise SystemExit(main())
