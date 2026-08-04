"""Verify that tracked release inputs contain no executable default credential."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_MIGRATION = Path(
    "backend/migrations/versions/20240926_add_password_to_expert_user.py"
)
REMEDIATION_MIGRATION = Path(
    "backend/migrations/versions/security_credential_remediation.py"
)
POLICY_VERIFIER = Path("scripts/verify_credential_policy.py")
LEGACY_HASH = "$2b$12$LQv3c1yqBWVHxkd0LQ4Q2e7Tq4lY8k9Z6p5v3nF7j8K2w4N9m1X8d"
FORBIDDEN_LITERALS = ("expert123", "password123", "admin123", "Pirooz13@!")
PASSWORD_ASSIGNMENT = re.compile(
    r"(?i)(?:password|passwd)\s*[:=]\s*['\"]([^<'\"]{4,})['\"]"
)
PLACEHOLDER_MARKERS = ("your-", "change_me", "operator-supplied", "<password>")


def tracked_files() -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=ROOT
    ).split(b"\0")
    return [Path(item.decode("utf-8")) for item in output if item]


def findings() -> list[str]:
    result: list[str] = []
    for relative in tracked_files():
        path = ROOT / relative
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        normalized = relative.as_posix()
        is_test = "/tests/" in f"/{normalized}" or Path(normalized).name.endswith(
            (".test.js", ".test.py")
        )
        if not is_test and relative not in {HISTORICAL_MIGRATION, POLICY_VERIFIER}:
            for literal in FORBIDDEN_LITERALS:
                if literal.lower() in text.lower():
                    result.append(f"{normalized}: forbidden shared credential literal")
            for match in PASSWORD_ASSIGNMENT.finditer(text):
                if not any(marker in match.group(1).lower() for marker in PLACEHOLDER_MARKERS):
                    result.append(f"{normalized}: executable password assignment")
        if LEGACY_HASH in text and relative not in {
            HISTORICAL_MIGRATION,
            REMEDIATION_MIGRATION,
            POLICY_VERIFIER,
        }:
            result.append(f"{normalized}: reusable legacy bcrypt outside remediation")

    seed = (ROOT / "backend/seed_experts.py").read_text(encoding="utf-8")
    if "BLOCKED:" not in seed or "bcrypt" in seed or "db.session" in seed:
        result.append("backend/seed_experts.py: compatibility path is not a refusal")
    return sorted(set(result))


def main() -> int:
    problems = findings()
    for problem in problems:
        print(f"credential-policy=FAIL path={problem}")
    if problems:
        print(f"credential-policy=FAIL findings={len(problems)}")
        return 1
    print("credential-policy=PASS findings=0 defaults=0 shared_hashes=historical-remediation-only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
