"""Smoke test for audit_chain. Run: python -m examples.audit_chain_smoke.

Writes 5 events, verifies the chain integrity, then tampers with one row
and confirms verify_chain() catches it.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from audit_chain import write_audit_event, verify_chain  # noqa: E402


def main() -> int:
    # Use a temp DB so we don't pollute the real audit_chain.db
    tmpdir = Path(tempfile.mkdtemp(prefix="audit_chain_smoke_"))
    db_path = tmpdir / "audit_chain.db"
    os.environ["AUDIT_CHAIN_DB_PATH"] = str(db_path)

    print(f"Smoke test using DB at {db_path}")

    # Write 5 events
    ids = []
    for i in range(5):
        rid = write_audit_event(
            caller_orch=f"orch-{i % 3}",
            pwcs_claim_uuid=f"test-uuid-{i}",
            layer="L2",
            model="model-a",
            cost_estimate_usd=0.001 * (i + 1),
            decision="allow" if i % 2 == 0 else "deny",
            reason=f"smoke-test-{i}",
            request_hash=hashlib.sha256(f"request-{i}".encode()).digest(),
            db_path=db_path,
        )
        ids.append(rid)
    print(f"Wrote 5 events: ids={ids}")

    # Verify chain
    ok = verify_chain(db_path=db_path)
    assert ok, "Chain should be valid after fresh writes"
    print(f"Chain verify after writes: PASS")

    # Tamper with one row's reason field
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "UPDATE audit_events SET reason='TAMPERED' WHERE id=?",
            (ids[2],),
        )
        conn.commit()
    finally:
        conn.close()
    print(f"Tampered with row id={ids[2]} (changed reason field)")

    # Verify chain detects the tamper
    ok_after_tamper = verify_chain(db_path=db_path)
    assert not ok_after_tamper, "Chain should detect tampering"
    print(f"Chain verify after tamper: FAIL (expected) — tamper detected")

    print("\nSmoke test PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
