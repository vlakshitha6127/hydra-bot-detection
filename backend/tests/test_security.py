import pytest
from backend.app.core.security import (
    hash_device_id,
    hash_ip_range,
    coarse_ip_prefix,
    truncate_hash,
)


def test_no_raw_identifiers_in_storage():
    raw_ip = "192.168.1.45"
    raw_device = "fingerprint_canvas_gpu_intel_hd620_uuid_9921"

    hashed_ip = hash_ip_range(raw_ip)
    hashed_dev = hash_device_id(raw_device)

    assert hashed_ip is not None
    assert hashed_dev is not None

    # Invariant I8: Raw identifier strings must never be present in the output hash
    assert raw_ip not in hashed_ip
    assert raw_device not in hashed_dev
    assert "192.168.1" not in hashed_ip

    # Hashing must be deterministic with the same key
    assert hash_ip_range(raw_ip) == hashed_ip
    assert hash_device_id(raw_device) == hashed_dev

    # Different raw values produce distinct keyed hashes
    assert hash_device_id("device_A") != hash_device_id("device_B")


def test_coarse_ip_prefix():
    assert coarse_ip_prefix("10.0.4.123") == "10.0.4.0/24"
    assert coarse_ip_prefix("172.16.20.99") == "172.16.20.0/24"


def test_null_handling():
    assert hash_device_id(None) is None
    assert hash_ip_range(None) is None
    assert truncate_hash(None) == "N/A"
