"""Verify all mandate YAML files conform to the schema.

Run: python -m examples.verify_mandate_schemas
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


REQUIRED_KEYS = {
    "id", "name", "version", "status", "authors", "domain", "applies_to",
    "rule", "verification", "violation_action", "references",
    "example_compliant", "example_violation",
}

ALLOWED_STATUSES = {"active", "draft", "deprecated"}

ALLOWED_VIOLATION_ACTIONS = {
    "alert_owner_and_log",
    "alert_owner_and_log_and_escalate",
    "block",
    "escalate_to_human",
    "refuse_and_log",
}

ALLOWED_DOMAINS = {
    "communications", "governance", "security", "data", "code",
    "thermal", "other",
}


def verify_file(path: Path) -> list[str]:
    """Return a list of error strings (empty if file is valid)."""
    errors: list[str] = []
    try:
        with open(path) as f:
            m = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [f"YAML parse error: {e}"]

    if not isinstance(m, dict):
        return ["top-level must be a mapping/dict"]

    missing = REQUIRED_KEYS - set(m.keys())
    if missing:
        errors.append(f"missing required keys: {sorted(missing)}")

    if "status" in m and m["status"] not in ALLOWED_STATUSES:
        errors.append(
            f"status='{m['status']}' not in {ALLOWED_STATUSES}"
        )

    if "violation_action" in m and m["violation_action"] not in ALLOWED_VIOLATION_ACTIONS:
        errors.append(
            f"violation_action='{m['violation_action']}' not in {ALLOWED_VIOLATION_ACTIONS}"
        )

    if "domain" in m and m["domain"] not in ALLOWED_DOMAINS:
        errors.append(
            f"domain='{m['domain']}' not in {ALLOWED_DOMAINS}"
        )

    if "applies_to" in m and not isinstance(m["applies_to"], list):
        errors.append("applies_to must be a list")
    elif "applies_to" in m and not m["applies_to"]:
        errors.append("applies_to must not be empty")

    if "id" in m and not isinstance(m["id"], str):
        errors.append("id must be a string")

    return errors


def main() -> int:
    mandate_dir = Path(__file__).parent.parent / "mandates"
    yaml_files = sorted(mandate_dir.glob("*.yaml"))

    if not yaml_files:
        print(f"ERROR: no YAML files found in {mandate_dir}", file=sys.stderr)
        return 1

    total_errors = 0
    for path in yaml_files:
        errors = verify_file(path)
        if errors:
            print(f"FAIL {path.name}:")
            for e in errors:
                print(f"  - {e}")
            total_errors += len(errors)
        else:
            print(f"PASS {path.name}")

    if total_errors:
        print(f"\n{total_errors} schema error(s) across {len(yaml_files)} mandate files.")
        return 1
    print(f"\nAll {len(yaml_files)} mandate files PASS schema check.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
