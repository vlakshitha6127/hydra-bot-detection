"""
Scoring and Evidence Gate Schemas for BreachX / HYDRA.
Separates:
1. Evidence Score (uncalibrated log-odds units)
2. Evidence Gate (active groups and eligibility conditions)
3. Policy Decision (ladder state)
As strictly required by §21.14 and Non-Negotiable Rule 8.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any


class SignalEvidence(BaseModel):
    signal_name: str
    family: str  # Identity, Creation timing, Behavioral timing, Content, Interaction, Rate
    group: str  # Provenance, Behavioral, Content, Context
    raw_value: float
    null_percentile: float
    calibrated_value: float
    weight: float
    log_odds_contribution: float


class GroupEvidence(BaseModel):
    group_name: str
    raw_sum: float
    capped_evidence: float
    is_active: bool
    threshold: float
    signals: List[SignalEvidence] = Field(default_factory=list)


class GateEvaluation(BaseModel):
    active_groups_count: int
    active_groups: List[str]
    has_active_provenance: bool
    gate_passed: bool
    gate_reason: str
    is_behavior_only: bool


class ClusterScoringResult(BaseModel):
    cluster_id: str
    window_index: int
    # 1. Output 1: Evidence Score (additive log-odds)
    evidence_score_current: float  # L_c(t)
    running_risk_score: float  # R_c(t)
    group_breakdown: Dict[str, GroupEvidence]
    # 2. Output 2: Evidence Gate
    gate: GateEvaluation
    # 3. Output 3: Review Queue Evaluation
    coordination_score: float  # C_c = sum of capped Behavioral + Content
    # Metadata
    member_count: int
    eligible_count: int
    ineligible_count: int
