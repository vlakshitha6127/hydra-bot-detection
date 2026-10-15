"""
Tamper-Evident Hash Chaining Module for BreachX / HYDRA.
Implements Milestone M14a, M14b, and Invariant I7:
- Canonical JSON serialization (sorted keys, fixed compact separators).
- SHA-256 hash chaining: hash_i = SHA-256(hash_{i-1} || canonical_json(record_i)).
- Integrity verification that returns OK or flags the exact index of first corruption.
"""

import json
import hashlib
from typing import Any, Dict, List, Tuple, Optional

GENESIS_HASH = "0" * 64


def canonical_json(data: Any) -> str:
    """
    Produces deterministic canonical JSON string:
    - Sorted keys
    - Compact separators (',', ':')
    - UTF-8 encoding without whitespace variances
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_record_hash(prev_hash: str, record_content: Dict[str, Any]) -> str:
    """
    Computes hash_i = SHA-256(prev_hash || canonical_json(record_content)).
    Note: record_content should NOT contain the 'record_hash' field itself.
    """
    canon = canonical_json(record_content)
    hasher = hashlib.sha256()
    hasher.update(prev_hash.encode("utf-8"))
    hasher.update(canon.encode("utf-8"))
    return hasher.hexdigest()


def verify_hash_chain(records: List[Dict[str, Any]]) -> Tuple[bool, Optional[int], str]:
    """
    Verifies an audit log chain.
    Each record must have 'prev_hash' and 'record_hash'.
    Returns:
        (is_valid, first_invalid_index, message)
    """
    if not records:
        return True, None, "Empty chain is valid."

    expected_prev = GENESIS_HASH

    for idx, rec in enumerate(records):
        # Extract metadata
        actual_prev = rec.get("prev_hash")
        actual_hash = rec.get("record_hash")

        if actual_prev != expected_prev:
            return (
                False,
                idx,
                f"Broken chain at record index {idx}: expected prev_hash '{expected_prev}', got '{actual_prev}'.",
            )

        # Exclude hash fields to reproduce payload
        content = {k: v for k, v in rec.items() if k not in ("prev_hash", "record_hash")}
        computed = compute_record_hash(expected_prev, content)

        if computed != actual_hash:
            return (
                False,
                idx,
                f"Hash mismatch at record index {idx}: computed '{computed}', stored '{actual_hash}'.",
            )

        expected_prev = actual_hash

    return True, None, f"Hash chain verified successfully across {len(records)} records."
