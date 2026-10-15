"""
Core Security and Privacy Module for BreachX / HYDRA.
Implements Milestone M13 and Invariant I8:
- No raw device identifiers or IP ranges stored at rest.
- Keyed HMAC-SHA256 hashing using a secret key held outside the data store.
- Coarse IP prefix aggregation (e.g., /24 for IPv4).
- Shortened hash representations for UI / evidence cards.
"""

import os
import hmac
import hashlib
from typing import Optional

# Secret key kept outside database storage (e.g. from environment variable)
DEFAULT_HMAC_SECRET = os.getenv(
    "HYDRA_HMAC_SECRET", "hydra_secret_production_key_seed_2026_breachx"
).encode("utf-8")


def hash_device_id(raw_device: Optional[str], secret_key: bytes = DEFAULT_HMAC_SECRET) -> Optional[str]:
    """
    Computes a keyed HMAC-SHA256 for a raw device fingerprint.
    Raw device identifier must never be stored.
    """
    if not raw_device:
        return None
    h = hmac.new(secret_key, raw_device.strip().encode("utf-8"), hashlib.sha256)
    return f"dev_{h.hexdigest()[:16]}"


def coarse_ip_prefix(raw_ip: str) -> str:
    """
    Reduces IP address to coarse subnet (/24 for IPv4) for data minimization.
    """
    parts = raw_ip.strip().split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
    return raw_ip.strip()


def hash_ip_range(raw_ip_or_prefix: Optional[str], secret_key: bytes = DEFAULT_HMAC_SECRET) -> Optional[str]:
    """
    Computes a keyed HMAC-SHA256 for an IP prefix.
    Prevents enumeration attacks against the 32-bit IPv4 address space.
    """
    if not raw_ip_or_prefix:
        return None
    coarse = coarse_ip_prefix(raw_ip_or_prefix)
    h = hmac.new(secret_key, coarse.encode("utf-8"), hashlib.sha256)
    return f"ip_{h.hexdigest()[:16]}"


def truncate_hash(hashed_val: Optional[str], length: int = 10) -> str:
    """
    Truncates a hash for presentation on evidence cards while preserving linkability.
    """
    if not hashed_val:
        return "N/A"
    return hashed_val[:length]
