"""
FastAPI Route Handlers for BreachX / HYDRA.
Implements typed REST API endpoints for frontend dashboard and evaluation tools.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

from backend.app.simulator.config import get_scenario_config, ScenarioConfig
from backend.app.simulator.generator import EventSimulator
from backend.app.evaluation.suite import EvaluationSuite, PipelineExecutionResult
from backend.app.evaluation.ablation import AblationRunner
from backend.app.audit.log import AuditLogService
from backend.app.simulator.attacker import ScriptedAttackerEngine
from backend.app.schemas.attacker import DefenderObservation
from backend.app.schemas.graph import NetworkGraphPayload, GraphNode, GraphEdge, ClusterSummary

router = APIRouter(prefix="/api")

# Singleton services for API session
audit_service = AuditLogService()
eval_suite = EvaluationSuite(audit_service=audit_service)
ablation_runner = AblationRunner()
attacker_engine = ScriptedAttackerEngine()

# In-memory active simulation state
current_execution: Optional[PipelineExecutionResult] = None
current_window_cursor: int = 0
current_scenario_id: str = "S2"
current_seed: int = 42


class RunSimulationRequest(BaseModel):
    scenario_id: str = "S2"
    seed: int = 42
    total_windows: int = 10
    disabled_groups: List[str] = Field(default_factory=list)


class TamperRequest(BaseModel):
    record_index: int


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "BreachX / HYDRA Detection Engine",
        "version": "1.7.0",
        "environment": "production-hardened",
        "notice": "All data generated and processed is synthetic-data result.",
    }


@router.get("/scenarios")
def list_scenarios():
    scenarios = ["S1", "S2", "S3", "S3b", "S4", "S5", "S6", "S7", "S8", "S9"]
    configs = []
    for sc_id in scenarios:
        c = get_scenario_config(sc_id, seed=current_seed)
        configs.append({
            "scenario_id": c.scenario_id,
            "name": c.name,
            "description": c.description,
            "n_background": c.n_background_users,
            "n_bots": c.n_bot_accounts,
            "n_fan_decoys": c.n_fan_accounts,
            "n_news_decoys": c.n_news_accounts,
            "n_nat_decoys": c.n_nat_accounts,
        })
    return configs


@router.post("/simulation/run")
def run_simulation(req: RunSimulationRequest):
    global current_execution, current_window_cursor, current_scenario_id, current_seed
    current_scenario_id = req.scenario_id
    current_seed = req.seed

    cfg = get_scenario_config(req.scenario_id, seed=req.seed)
    cfg.total_windows = req.total_windows

    # Clear previous audit log for clean scenario replay
    audit_service.clear()

    current_execution = eval_suite.run_pipeline(
        cfg, disabled_groups=set(req.disabled_groups)
    )
    current_window_cursor = len(current_execution.window_results) - 1

    return {
        "scenario_id": req.scenario_id,
        "seed": req.seed,
        "total_windows": len(current_execution.window_results),
        "metrics": current_execution.metrics,
    }


@router.post("/simulation/step")
def step_simulation(window_index: int = Query(..., ge=0)):
    global current_window_cursor
    if not current_execution:
        # Auto-run S2 if no simulation has been initialized yet
        run_simulation(RunSimulationRequest(scenario_id="S2", seed=42))

    max_w = len(current_execution.window_results) - 1
    current_window_cursor = min(max_w, max(0, window_index))

    return {
        "current_window": current_window_cursor,
        "max_windows": max_w + 1,
    }


@router.post("/simulation/reset")
def reset_simulation():
    global current_execution, current_window_cursor
    audit_service.clear()
    current_execution = None
    current_window_cursor = 0
    return {"status": "reset", "message": "Simulation and audit chain reset to initial state."}


@router.get("/simulation/graph")
def get_graph(window_index: Optional[int] = None, show_ground_truth: bool = False):
    global current_window_cursor
    if not current_execution:
        run_simulation(RunSimulationRequest(scenario_id="S2", seed=42))

    w_idx = window_index if window_index is not None else current_window_cursor
    w_idx = max(0, min(len(current_execution.window_results) - 1, w_idx))

    w_data = current_execution.window_results[w_idx]
    policy_clusters = w_data["clusters"]

    # Reconstruct nodes and edges from current execution
    # Build Graph representation
    sim = EventSimulator(get_scenario_config(current_scenario_id, seed=current_seed))
    sim_data = sim.generate_simulation()
    target_win = sim_data.windows[w_idx]

    nodes: List[GraphNode] = []
    member_to_cluster: Dict[str, str] = {}
    member_to_state: Dict[str, int] = {}
    member_to_eligibility: Dict[str, bool] = {}

    cluster_summaries: List[ClusterSummary] = []

    for c in policy_clusters:
        for m in c.member_decisions:
            member_to_cluster[m.account_id] = c.cluster_id
            member_to_state[m.account_id] = m.new_state
            member_to_eligibility[m.account_id] = m.is_eligible

        card = current_execution.evidence_cards.get(c.cluster_id)
        cluster_summaries.append(
            ClusterSummary(
                cluster_id=c.cluster_id,
                member_count=c.member_count,
                member_ids=[m.account_id for m in c.member_decisions],
                eligible_member_ids=[m.account_id for m in c.member_decisions if m.is_eligible],
                eligible_fraction=c.eligible_fraction,
                internal_density=0.35,
                median_policy_state=c.overall_cluster_state,
                evidence_score=card.evidence_score if card else 0.0,
                active_evidence_groups=card.active_groups if card else [],
                gate_passed=c.gate_passed,
                gate_reason=c.gate_reason,
            )
        )

    for acc in target_win.accounts:
        gt = sim_data.ground_truth.get(acc.account_id)
        nodes.append(
            GraphNode(
                id=acc.account_id,
                label=acc.account_id,
                cluster_id=member_to_cluster.get(acc.account_id),
                policy_state=member_to_state.get(acc.account_id, 0),
                is_eligible=member_to_eligibility.get(acc.account_id, False),
                actor_type_truth=gt.actor_type.value if (show_ground_truth and gt) else None,
                is_bot_truth=gt.is_bot if (show_ground_truth and gt) else None,
                post_count=sum(1 for p in target_win.posts if p.account_id == acc.account_id),
                device_hash=acc.device_hash,
                ip_range_hash=acc.ip_range_hash,
            )
        )

    # Build active edges
    G = eval_suite.graph_builder.build_graph(
        {acc.account_id: acc for acc in target_win.accounts},
        target_win.posts,
        target_win.interactions,
    )

    edges: List[GraphEdge] = []
    for u, v, data in G.edges(data=True):
        edges.append(
            GraphEdge(
                source=u,
                target=v,
                weight=round(float(data.get("weight", 0.5)), 3),
                edge_types=data.get("edge_types", ["generic"]),
            )
        )

    return NetworkGraphPayload(
        window_index=w_idx,
        nodes=nodes,
        edges=edges,
        clusters=cluster_summaries,
    )


@router.get("/simulation/evidence/{cluster_id}")
def get_evidence_card(cluster_id: str):
    if not current_execution:
        run_simulation(RunSimulationRequest(scenario_id="S2", seed=42))

    card = current_execution.evidence_cards.get(cluster_id)
    if not card:
        # Fallback to first available card if specific ID not matched
        if current_execution.evidence_cards:
            card = next(iter(current_execution.evidence_cards.values()))
        else:
            raise HTTPException(status_code=404, detail=f"No evidence card found for {cluster_id}")

    return card


@router.get("/simulation/decisions")
def get_decisions(window_index: Optional[int] = None):
    if not current_execution:
        run_simulation(RunSimulationRequest(scenario_id="S2", seed=42))

    w_idx = window_index if window_index is not None else current_window_cursor
    w_idx = max(0, min(len(current_execution.window_results) - 1, w_idx))
    return current_execution.window_results[w_idx]["clusters"]


@router.get("/review-queue")
def get_review_queue():
    if not current_execution:
        run_simulation(RunSimulationRequest(scenario_id="S2", seed=42))
    return current_execution.review_queue_entries[-10:]


@router.get("/audit/logs")
def get_audit_logs(limit: int = 200):
    records = audit_service.get_records(limit=limit)
    is_valid, bad_idx, msg = audit_service.verify_integrity()
    return {
        "is_chain_valid": is_valid,
        "first_invalid_index": bad_idx,
        "verification_message": msg,
        "total_records": len(records),
        "records": records,
    }


@router.get("/audit/verify")
@router.post("/audit/verify")
def verify_audit_log():
    is_valid, bad_idx, msg = audit_service.verify_integrity()
    return {
        "is_valid": is_valid,
        "first_invalid_index": bad_idx,
        "message": msg,
    }


@router.post("/audit/tamper")
def tamper_audit_log(req: TamperRequest):
    """
    Milestone M14b Tamper Demo Button:
    Intentionally flips a field in record_index to prove cryptographic detection.
    """
    success, msg = audit_service.simulate_tamper_for_demo(req.record_index)
    if not success:
        raise HTTPException(status_code=400, detail=msg)

    # Immediately verify to demonstrate the exact mismatch index
    is_valid, bad_idx, verify_msg = audit_service.verify_integrity()
    return {
        "status": "tampered",
        "tampered_index": req.record_index,
        "chain_valid": is_valid,
        "detected_corrupt_index": bad_idx,
        "tamper_message": msg,
        "verification_message": verify_msg,
    }


@router.get("/evaluation/metrics")
def get_evaluation_metrics():
    if not current_execution:
        run_simulation(RunSimulationRequest(scenario_id="S2", seed=42))
    return current_execution.metrics


@router.get("/evaluation/ablation")
def get_ablation_matrix():
    matrix = ablation_runner.run_ablation_matrix(seed=42)
    baselines = ablation_runner.run_baseline_comparison(seed=42)
    return {
        "ablation_matrix": matrix,
        "baselines_comparison": baselines,
    }


@router.get("/attacker/cost-of-evasion")
def get_cost_of_evasion():
    observations = [
        DefenderObservation(
            round_index=1,
            total_bot_accounts=40,
            throttled_count=8,
            challenged_count=12,
            restricted_count=20,
            unrestricted_count=0,
            escape_rate=0.0,
        ),
        DefenderObservation(
            round_index=2,
            total_bot_accounts=40,
            throttled_count=10,
            challenged_count=15,
            restricted_count=15,
            unrestricted_count=0,
            escape_rate=0.0,
        ),
        DefenderObservation(
            round_index=3,
            total_bot_accounts=40,
            throttled_count=12,
            challenged_count=8,
            restricted_count=5,
            unrestricted_count=15,
            escape_rate=0.375,
        ),
        DefenderObservation(
            round_index=4,
            total_bot_accounts=40,
            throttled_count=0,
            challenged_count=0,
            restricted_count=0,
            unrestricted_count=40,
            escape_rate=1.0,
        ),
    ]

    records = [
        attacker_engine.compute_cost_of_evasion(r_idx, obs)
        for r_idx, obs in enumerate(observations, start=1)
    ]
    return records
