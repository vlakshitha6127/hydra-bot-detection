"""
Attacker and Cost-of-Evasion Schemas for BreachX / HYDRA.
Implements Sections 10.1, 10.2, and 21.16.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any


class AttackerTactics(BaseModel):
    round_index: int
    name: str
    description: str
    timing_jitter: float  # [0, 1]
    paraphrase_rate: float  # [0, 1]
    shared_devices_count: int  # Device pool size
    posting_rate_multiplier: float  # Speed throttle
    signup_spread_days: float


class DefenderObservation(BaseModel):
    round_index: int
    total_bot_accounts: int
    throttled_count: int
    challenged_count: int
    restricted_count: int
    unrestricted_count: int
    escape_rate: float  # Fraction of bot accounts never reaching state >= 1


class CostOfEvasionRecord(BaseModel):
    round_index: int
    tactic_name: str
    # Primary axis (§10.2):
    throughput_retained_pct: float  # Posts delivered per account-hour relative to unevaded
    # Secondary axes (§10.2):
    reach_retained_pct: float  # Amplification reach
    distinct_devices_required: int
    distinct_ips_required: int
    escape_rate_pct: float
    detection_state_summary: str
