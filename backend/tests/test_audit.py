import pytest
from backend.app.audit.hasher import (
    canonical_json,
    compute_record_hash,
    verify_hash_chain,
    GENESIS_HASH,
)


def test_canonical_json_determinism():
    dict1 = {"z": 10, "a": "hello", "m": [3, 2, 1]}
    dict2 = {"a": "hello", "m": [3, 2, 1], "z": 10}
    assert canonical_json(dict1) == canonical_json(dict2)
    assert canonical_json(dict1) == '{"a":"hello","m":[3,2,1],"z":10}'


def test_hash_chain_creation_and_verification():
    records = []
    prev_hash = GENESIS_HASH

    for i in range(5):
        payload = {
            "window": i,
            "cluster_id": f"c_{i}",
            "evidence_score": 2.5 + i,
            "policy_state": 1,
        }
        rec_hash = compute_record_hash(prev_hash, payload)
        record = {
            **payload,
            "prev_hash": prev_hash,
            "record_hash": rec_hash,
        }
        records.append(record)
        prev_hash = rec_hash

    is_valid, bad_idx, msg = verify_hash_chain(records)
    assert is_valid is True
    assert bad_idx is None
    assert "verified successfully" in msg


def test_tamper_detection_at_exact_index():
    records = []
    prev_hash = GENESIS_HASH

    for i in range(10):
        payload = {
            "window": i,
            "cluster_id": f"c_{i}",
            "action": "throttle" if i > 2 else "observe",
        }
        rec_hash = compute_record_hash(prev_hash, payload)
        record = {
            **payload,
            "prev_hash": prev_hash,
            "record_hash": rec_hash,
        }
        records.append(record)
        prev_hash = rec_hash

    # Now tamper with record at index 4 (e.g. attacker tries to change 'action' to 'observe')
    records[4]["action"] = "observe"

    is_valid, bad_idx, msg = verify_hash_chain(records)
    # Must immediately identify index 4 as the corrupt record
    assert is_valid is False
    assert bad_idx == 4
    assert "Hash mismatch at record index 4" in msg
