"""audit_chain — tamper-evident SQLite-WAL hash chain for AI decisions.

Each row is hashed with the prior row's hash. Any modification to a
historical row breaks the chain, detectable by verify_chain().

Public API:
    write_audit_event(...) -> int (row id)
    verify_chain() -> bool
    health_check(timeout=1.0) -> dict

Usage:
    import hashlib
    from audit_chain import write_audit_event, verify_chain

    write_audit_event(
        caller_orch="orch-1",
        pwcs_claim_uuid="abc-123",
        layer="L2",
        model="model-a",
        cost_estimate_usd=0.0025,
        decision="allow",
        reason="policy_check_passed",
        request_hash=hashlib.sha256(request_body).digest(),
    )

    assert verify_chain() is True

The managed CruxApex product adds deployment, retention policy, access
control, evidence export, and customer-specific operations around this core.

This OSS layer ships the core hash-chain implementation plus a smoke example
for verification and tamper detection.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import time
from pathlib import Path
from typing import Optional


__version__ = "0.1.0"
__all__ = [
    "write_audit_event",
    "verify_chain",
    "health_check",
    "AuditChainError",
    "ChainBrokenError",
]


DEFAULT_DB_PATH = Path(
    os.environ.get("AUDIT_CHAIN_DB_PATH", "./audit_chain.db")
)


class AuditChainError(Exception):
    """Base error for audit chain operations."""


class ChainBrokenError(AuditChainError):
    """Raised when verify_chain() detects a hash mismatch."""


def _connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Open SQLite connection in WAL mode."""
    path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _init_db(conn: sqlite3.Connection) -> None:
    """Create audit_events table if it doesn't exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_nanos_utc INTEGER NOT NULL,
            caller_orch TEXT NOT NULL,
            pwcs_claim_uuid TEXT NOT NULL,
            layer TEXT NOT NULL,
            model TEXT NOT NULL,
            cost_estimate_usd REAL NOT NULL,
            decision TEXT NOT NULL CHECK(decision IN ('allow','deny','escalate')),
            reason TEXT NOT NULL,
            request_hash BLOB NOT NULL,
            prior_chain_hash BLOB,
            chain_hash BLOB NOT NULL
        )
        """
    )
    conn.commit()


def _compute_chain_hash(
    ts_nanos_utc: int,
    caller_orch: str,
    pwcs_claim_uuid: str,
    layer: str,
    model: str,
    cost_estimate_usd: float,
    decision: str,
    reason: str,
    request_hash: bytes,
    prior_chain_hash: Optional[bytes],
) -> bytes:
    """SHA-256 of canonical row encoding + prior hash."""
    parts = [
        str(ts_nanos_utc).encode(),
        caller_orch.encode(),
        pwcs_claim_uuid.encode(),
        layer.encode(),
        model.encode(),
        f"{cost_estimate_usd:.10f}".encode(),
        decision.encode(),
        reason.encode(),
        request_hash,
        prior_chain_hash or b"",
    ]
    return hashlib.sha256(b"|".join(parts)).digest()


def write_audit_event(
    *,
    caller_orch: str,
    pwcs_claim_uuid: str,
    layer: str,
    model: str,
    cost_estimate_usd: float = 0.0,
    decision: str = "allow",
    reason: str = "",
    request_hash: bytes,
    db_path: Optional[Path] = None,
    ts_nanos_utc: Optional[int] = None,
) -> int:
    """Append an audit event to the chain. Returns the row id."""
    if decision not in ("allow", "deny", "escalate"):
        raise AuditChainError(f"invalid decision: {decision}")

    ts = ts_nanos_utc if ts_nanos_utc is not None else time.time_ns()

    conn = _connect(db_path)
    try:
        _init_db(conn)
        prior_hash_row = conn.execute(
            "SELECT chain_hash FROM audit_events ORDER BY id DESC LIMIT 1"
        ).fetchone()
        prior_chain_hash = prior_hash_row[0] if prior_hash_row else None
        chain_hash = _compute_chain_hash(
            ts, caller_orch, pwcs_claim_uuid, layer, model,
            cost_estimate_usd, decision, reason, request_hash, prior_chain_hash,
        )
        cursor = conn.execute(
            """
            INSERT INTO audit_events (
                ts_nanos_utc, caller_orch, pwcs_claim_uuid, layer, model,
                cost_estimate_usd, decision, reason, request_hash,
                prior_chain_hash, chain_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ts, caller_orch, pwcs_claim_uuid, layer, model,
                cost_estimate_usd, decision, reason, request_hash,
                prior_chain_hash, chain_hash,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def verify_chain(db_path: Optional[Path] = None) -> bool:
    """Walk the chain front-to-back, recomputing each hash.

    Returns True if every row's chain_hash matches the recomputed value
    AND every row's prior_chain_hash matches the prior row's chain_hash.
    Returns False otherwise.
    """
    conn = _connect(db_path)
    try:
        _init_db(conn)
        rows = conn.execute(
            """
            SELECT
                id, ts_nanos_utc, caller_orch, pwcs_claim_uuid, layer, model,
                cost_estimate_usd, decision, reason, request_hash,
                prior_chain_hash, chain_hash
            FROM audit_events ORDER BY id ASC
            """
        ).fetchall()
        prior_hash: Optional[bytes] = None
        for row in rows:
            (
                _id, ts, orch, pwcs, layer, model, cost, decision,
                reason, req_hash, stored_prior, stored_chain,
            ) = row
            if stored_prior != prior_hash:
                return False
            recomputed = _compute_chain_hash(
                ts, orch, pwcs, layer, model, cost, decision, reason,
                req_hash, prior_hash,
            )
            if recomputed != stored_chain:
                return False
            prior_hash = stored_chain
        return True
    finally:
        conn.close()


def health_check(timeout: float = 1.0, db_path: Optional[Path] = None) -> dict:
    """Quick health check for service-level monitoring."""
    start = time.monotonic()
    try:
        conn = _connect(db_path)
        try:
            _init_db(conn)
            count_row = conn.execute("SELECT COUNT(*) FROM audit_events").fetchone()
            row_count = count_row[0] if count_row else 0
        finally:
            conn.close()
        elapsed = time.monotonic() - start
        if elapsed > timeout:
            return {"ok": False, "reason": "slow", "elapsed_seconds": elapsed}
        return {"ok": True, "row_count": row_count, "elapsed_seconds": elapsed}
    except sqlite3.DatabaseError as e:
        return {"ok": False, "reason": "db_error", "error": str(e)}
