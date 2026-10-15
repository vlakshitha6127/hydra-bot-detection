"""
Graph Data Schemas for BreachX / HYDRA.
Defines Node, Edge, Cluster, and GraphPayload for API and Frontend.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any


class GraphNode(BaseModel):
    id: str
    label: str
    cluster_id: Optional[str] = None
    policy_state: int = 0  # 0: Observe, 1: Throttle, 2: Challenge, 3: Restriction, 4: Escalation
    is_eligible: bool = False
    actor_type_truth: Optional[str] = None  # Hidden or judge toggle only
    is_bot_truth: Optional[bool] = None  # Hidden or judge toggle only
    post_count: int = 0
    device_hash: Optional[str] = None
    ip_range_hash: Optional[str] = None


class GraphEdge(BaseModel):
    source: str
    target: str
    weight: float
    edge_types: List[str] = Field(default_factory=list)  # "device", "ip", "content", "timing", "interaction"


class ClusterSummary(BaseModel):
    cluster_id: str
    member_count: int
    member_ids: List[str]
    eligible_member_ids: List[str]
    eligible_fraction: float
    internal_density: float
    median_policy_state: int
    evidence_score: float
    active_evidence_groups: List[str]
    gate_passed: bool
    gate_reason: str


class NetworkGraphPayload(BaseModel):
    window_index: int
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    clusters: List[ClusterSummary]
