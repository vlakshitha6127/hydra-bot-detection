"""
Explainability and Evidence Card Schemas for BreachX / HYDRA.
Implements Sections 11, 20.5, and Invariant I4.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any


class CounterfactualOutcome(BaseModel):
    removed_group_or_signal: str
    original_state: int
    counterfactual_state: int
    delta_log_odds: float
    explanation: str


class RepresentativeSample(BaseModel):
    sample_type: str  # "post_pair", "device_group", "timing_burst"
    description: str
    evidence_data: Dict[str, Any]


class EvidenceCard(BaseModel):
    cluster_id: str
    window_index: int
    member_count: int
    eligible_count: int
    eligible_fraction: float
    creation_time_span_seconds: float
    current_state: int
    state_label: str
    risk_trend: str  # "increasing", "steady", "decaying"
    running_risk: float
    evidence_score: float

    # Signal contributions grouped by evidence group
    group_contributions: Dict[str, float]
    signal_contributions: List[Dict[str, Any]]

    # Gate status
    active_groups: List[str]
    missing_groups: List[str]
    has_provenance: bool
    gate_passed: bool
    gate_message: str

    # Exact counterfactuals
    counterfactuals: List[CounterfactualOutcome]

    # Concrete samples for analyst inspection
    representative_samples: List[RepresentativeSample]

    # Ineligible member summary
    ineligible_members: List[str] = Field(default_factory=list)
