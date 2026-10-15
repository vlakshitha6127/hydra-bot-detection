"""
Policy Engine Schemas for BreachX / HYDRA.
Defines response states, transitions, member eligibility, and decision records.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import IntEnum


class ResponseState(IntEnum):
    OBSERVE = 0
    THROTTLE = 1
    CHALLENGE = 2
    RESTRICTION = 3
    ESCALATION = 4


class AccountPolicyDecision(BaseModel):
    account_id: str
    cluster_id: str
    window_index: int
    prev_state: int
    new_state: int
    rule_fired: str
    is_eligible: bool
    eligibility_reason: str
    evidence_score: float
    running_risk: float
    persistence_count: int
    active_groups: List[str]
    has_provenance: bool
    ttl_remaining: int = 0


class ClusterPolicyDecision(BaseModel):
    cluster_id: str
    window_index: int
    median_state_eligible: int
    overall_cluster_state: int
    member_count: int
    eligible_count: int
    eligible_fraction: float
    gate_passed: bool
    gate_reason: str
    rule_fired: str
    member_decisions: List[AccountPolicyDecision] = Field(default_factory=list)
