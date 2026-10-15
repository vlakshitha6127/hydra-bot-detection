"""
Append-Only Hash-Chained Audit Log Service for BreachX / HYDRA.
Implements Milestone M14a, M14b, Invariant I5, and Invariant I7:
- Deterministic append-only storage in SQLite or memory.
- Hash-chaining each decision: h_i = SHA256(h_{i-1} || canonical_json(record_i)).
- Interactive tamper simulation and verification method that returns first corrupted index.
"""

import sqlite3
import os
from typing import List, Dict, Any, Tuple, Optional

from backend.app.audit.hasher import (
    GENESIS_HASH,
    compute_record_hash,
    verify_hash_chain,
    canonical_json,
)


class AuditLogService:
    """
    Cryptographically chained append-only decision log.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self._in_memory_records: List[Dict[str, Any]] = []
        self._current_head_hash = GENESIS_HASH

        if self.db_path:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self._init_db()
            self._load_from_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    record_index INTEGER PRIMARY KEY AUTOINCREMENT,
                    window_index INTEGER,
                    cluster_id TEXT,
                    account_id TEXT,
                    prev_state INTEGER,
                    new_state INTEGER,
                    rule_fired TEXT,
                    evidence_score REAL,
                    running_risk REAL,
                    is_eligible INTEGER,
                    prev_hash TEXT,
                    record_hash TEXT,
                    payload_json TEXT,
                    timestamp REAL
                )
                """
            )
            conn.commit()

    def _load_from_db(self) -> None:
        if not self.db_path:
            return
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT payload_json, prev_hash, record_hash FROM audit_log ORDER BY record_index ASC")
            rows = cursor.fetchall()
            self._in_memory_records.clear()
            for payload_str, p_hash, r_hash in rows:
                import json
                rec = json.loads(payload_str)
                rec["prev_hash"] = p_hash
                rec["record_hash"] = r_hash
                self._in_memory_records.append(rec)
            if self._in_memory_records:
                self._current_head_hash = self._in_memory_records[-1]["record_hash"]

    def append_decision(self, decision_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Appends a decision to the hash chain and stores it.
        """
        prev_hash = self._current_head_hash
        rec_idx = len(self._in_memory_records)
        content = {k: v for k, v in decision_payload.items() if k not in ("prev_hash", "record_hash", "record_index")}
        content["record_index"] = rec_idx
        record_hash = compute_record_hash(prev_hash, content)

        record = {
            **content,
            "prev_hash": prev_hash,
            "record_hash": record_hash,
        }

        self._in_memory_records.append(record)
        self._current_head_hash = record_hash

        if self.db_path:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO audit_log (
                        window_index, cluster_id, account_id, prev_state, new_state,
                        rule_fired, evidence_score, running_risk, is_eligible,
                        prev_hash, record_hash, payload_json, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.get("window_index", 0),
                        record.get("cluster_id", "unknown"),
                        record.get("account_id", "unknown"),
                        record.get("prev_state", 0),
                        record.get("new_state", 0),
                        record.get("rule_fired", ""),
                        record.get("evidence_score", 0.0),
                        record.get("running_risk", 0.0),
                        1 if record.get("is_eligible", False) else 0,
                        prev_hash,
                        record_hash,
                        canonical_json(content),
                        record.get("timestamp", 0.0),
                    ),
                )
                conn.commit()

        return record

    def get_records(self, limit: int = 1000) -> List[Dict[str, Any]]:
        return self._in_memory_records[-limit:]

    def verify_integrity(self) -> Tuple[bool, Optional[int], str]:
        """
        Verifies cryptographic integrity of entire chain.
        """
        return verify_hash_chain(self._in_memory_records)

    def simulate_tamper_for_demo(self, record_index: int) -> Tuple[bool, str]:
        """
        M14b Interactive Demo Feature:
        Simulates an unauthorized modification to an existing audit record.
        """
        if 0 <= record_index < len(self._in_memory_records):
            # Tamper with rule_fired field
            self._in_memory_records[record_index]["rule_fired"] += " [TAMPERED_BY_ADVERSARY]"
            return True, f"Record {record_index} modified intentionally to demonstrate tamper detection."
        return False, "Invalid record index."

    def clear(self) -> None:
        self._in_memory_records.clear()
        self._current_head_hash = GENESIS_HASH
        if self.db_path and os.path.exists(self.db_path):
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM audit_log")
                conn.commit()
