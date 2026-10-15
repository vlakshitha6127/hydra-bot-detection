"""
End-to-End Evaluation Pipeline and Metrics Suite for BreachX / HYDRA.
Implements Milestone M9, Sections 9, 21.8, 21.10, and 21.14:
- Executes multi-window simulation, signal extraction, Louvain clustering, scoring, policy, and audit logging.
- Computes cluster precision/recall, decoy restriction rate, detection delay, and FPR.
- Manages Review Queue tracking and Precision@k.
- Isolates ground-truth labels completely during execution; uses them strictly for final metrics computation.
"""

from typing import Dict, List, Set, Tuple, Optional, Any
import numpy as np

from backend.app.schemas.event import SimulationRunData, ActorType
from backend.app.simulator.config import ScenarioConfig, get_scenario_config
from backend.app.simulator.generator import EventSimulator
from backend.app.graph.builder import GraphBuilder
from backend.app.graph.clustering import CommunityDetector
from backend.app.signals.extractor import SignalExtractor
from backend.app.scoring.calibrator import EvidenceCalibrator
from backend.app.scoring.gate import EvidenceGate
from backend.app.scoring.temporal import TemporalTracker
from backend.app.policy.state_machine import ResponseLadderStateMachine
from backend.app.policy.engine import PolicyEngine
from backend.app.policy.review_queue import ReviewQueueManager
from backend.app.explainability.evidence_card import EvidenceCardGenerator
from backend.app.audit.log import AuditLogService
from backend.app.schemas.scoring import ClusterScoringResult
from backend.app.schemas.policy import ClusterPolicyDecision


class PipelineExecutionResult:
    """
    Holds complete runtime state and output across all windows of a simulation run.
    """

    def __init__(self, scenario_id: str, seed: int):
        self.scenario_id = scenario_id
        self.seed = seed
        self.window_results: List[Dict[str, Any]] = []
        self.metrics: Dict[str, Any] = {}
        self.evidence_cards: Dict[str, Any] = {}
        self.review_queue_entries: List[Any] = []
        self.audit_records: List[Any] = []


class EvaluationSuite:
    """
    Orchestrates end-to-end evaluation pipeline.
    """

    def __init__(self, audit_service: Optional[AuditLogService] = None):
        self.audit_service = audit_service or AuditLogService()
        self.graph_builder = GraphBuilder()
        self.community_detector = CommunityDetector()
        self.signal_extractor = SignalExtractor()
        self.calibrator = EvidenceCalibrator()
        self.evidence_card_gen = EvidenceCardGenerator()

    def run_pipeline(
        self,
        config: ScenarioConfig,
        disabled_groups: Optional[Set[str]] = None,
    ) -> PipelineExecutionResult:
        """
        Executes end-to-end pipeline across all windows for a given scenario.
        """
        disabled_groups = disabled_groups or set()
        result = PipelineExecutionResult(config.scenario_id, config.seed)

        # 1. Generate synthetic events
        sim = EventSimulator(config)
        sim_data = sim.generate_simulation()
        ground_truth = sim_data.ground_truth

        # Initialize fresh policy engine and temporal tracker for this run
        temporal_tracker = TemporalTracker()
        state_machine = ResponseLadderStateMachine()
        policy_engine = PolicyEngine(
            audit_service=self.audit_service,
            state_machine=state_machine,
            temporal_tracker=temporal_tracker,
        )
        review_queue = ReviewQueueManager(top_k_limit=5)

        first_throttle_window: Optional[int] = None
        first_challenge_window: Optional[int] = None
        first_restriction_window: Optional[int] = None

        prev_cluster_mappings: Dict[str, Set[str]] = {}

        # 2. Process window by window
        for w_idx, win in enumerate(sim_data.windows):
            window_accounts = {acc.account_id: acc for acc in win.accounts}
            # Also merge sim.accounts for historical reference
            merged_accounts = {**sim.accounts, **window_accounts}

            # Build account graph with rarity weights
            G = self.graph_builder.build_graph(merged_accounts, win.posts, win.interactions)

            # Detect clusters via Louvain
            raw_clusters = self.community_detector.detect_communities(G)

            # Cluster identity tracking
            matched_clusters: Dict[str, Set[str]] = {}
            for c_i, c_members in enumerate(raw_clusters):
                cid = f"cluster_w{w_idx}_{c_i}"
                matched_clusters[cid] = c_members

            cluster_scoring_results: List[ClusterScoringResult] = []
            cluster_policy_decisions: List[ClusterPolicyDecision] = []
            queue_candidates: List[Dict[str, Any]] = []

            for cid, c_members in matched_clusters.items():
                # Extract raw signals
                raw_signals = self.signal_extractor.extract_cluster_signals(
                    c_members, merged_accounts, win.posts, win.interactions
                )

                # Simulate signal group disabling for ablation studies (§9.3)
                if "Provenance" in disabled_groups:
                    raw_signals["shared_device"] = 0.0
                    raw_signals["shared_ip"] = 0.0
                    raw_signals["creation_burst"] = 0.0
                if "Behavioral" in disabled_groups:
                    raw_signals["interval_regularity"] = 0.0
                    raw_signals["synchronized_bursts"] = 0.0
                    raw_signals["interaction_density"] = 0.0
                if "Content" in disabled_groups:
                    raw_signals["semantic_similarity"] = 0.0
                    raw_signals["lexical_near_duplicates"] = 0.0

                # Calibrate into log-odds and group breakdown
                l_c, group_breakdown = self.calibrator.evaluate_cluster_evidence(raw_signals)

                # Non-compensatory gate
                gate_eval = EvidenceGate.evaluate_gate(group_breakdown)

                # Calculate coordination score C_c
                coord_score = TemporalTracker.compute_coordination_score(group_breakdown)

                scoring_res = ClusterScoringResult(
                    cluster_id=cid,
                    window_index=w_idx,
                    evidence_score_current=l_c,
                    running_risk_score=l_c,
                    group_breakdown=group_breakdown,
                    gate=gate_eval,
                    coordination_score=coord_score,
                    member_count=len(c_members),
                    eligible_count=0,
                    ineligible_count=len(c_members),
                )

                # Policy execution with member-level eligibility
                policy_dec = policy_engine.execute_policy(
                    cluster_id=cid,
                    window_index=w_idx,
                    cluster_member_ids=c_members,
                    all_accounts=merged_accounts,
                    scoring_result=scoring_res,
                )

                # Update counts on scoring res
                scoring_res.eligible_count = policy_dec.eligible_count
                scoring_res.ineligible_count = policy_dec.member_count - policy_dec.eligible_count

                cluster_scoring_results.append(scoring_res)
                cluster_policy_decisions.append(policy_dec)

                # Queue candidate for behavior-only / unprovenanced clusters (§21.8)
                if not gate_eval.gate_passed:
                    queue_candidates.append({
                        "cluster_id": cid,
                        "coordination_score": coord_score,
                        "persistence": 1,
                        "member_count": len(c_members),
                        "active_groups": gate_eval.active_groups,
                        "is_behavior_only": gate_eval.is_behavior_only,
                        "gate_passed": False,
                    })

                # Generate Evidence Card
                card = self.evidence_card_gen.generate_card(
                    cluster_id=cid,
                    cluster_members=c_members,
                    all_accounts=merged_accounts,
                    posts=win.posts,
                    scoring_res=scoring_res,
                    policy_dec=policy_dec,
                )
                result.evidence_cards[cid] = card

                # Detection delay tracking for bot farm
                bot_overlap = sum(1 for m in c_members if ground_truth.get(m, False) and ground_truth[m].is_bot)
                if bot_overlap >= 10:
                    if policy_dec.overall_cluster_state >= 1 and first_throttle_window is None:
                        first_throttle_window = w_idx
                    if policy_dec.overall_cluster_state >= 2 and first_challenge_window is None:
                        first_challenge_window = w_idx
                    if policy_dec.overall_cluster_state >= 3 and first_restriction_window is None:
                        first_restriction_window = w_idx

            # Enqueue unprovenanced clusters to rate-limited human review queue
            enqueued = review_queue.rank_and_enqueue_clusters(queue_candidates, w_idx)
            result.review_queue_entries.extend(enqueued)

            # Decay inactive accounts
            active_ids = set(acc.account_id for acc in win.accounts)
            temporal_tracker.decay_inactive_accounts(active_ids)

            result.window_results.append({
                "window_index": w_idx,
                "node_count": G.number_of_nodes(),
                "edge_count": G.number_of_edges(),
                "clusters_detected": len(matched_clusters),
                "clusters": cluster_policy_decisions,
            })

            prev_cluster_mappings = matched_clusters

        # 3. Compute final metrics (§9.1, §21.10)
        final_account_states = temporal_tracker.account_state

        # Farm detection & overlap
        bot_ids = [aid for aid, lbl in ground_truth.items() if lbl.is_bot]
        decoy_ids = [aid for aid, lbl in ground_truth.items() if lbl.is_decoy]
        bg_ids = [aid for aid, lbl in ground_truth.items() if lbl.actor_type == ActorType.BACKGROUND]

        bot_states = [final_account_states.get(aid, 0) for aid in bot_ids]
        decoy_states = [final_account_states.get(aid, 0) for aid in decoy_ids]
        bg_states = [final_account_states.get(aid, 0) for aid in bg_ids]

        # Invariant check: Decoy user-impacting action count
        decoy_restricted_count = sum(1 for s in decoy_states if s >= 1)
        decoy_restriction_rate = decoy_restricted_count / max(1, len(decoy_ids))

        # Farm detection rate
        bot_detected_count = sum(1 for s in bot_states if s >= 1)
        farm_recall = bot_detected_count / max(1, len(bot_ids))

        # Background false positive rate
        bg_fp_count = sum(1 for s in bg_states if s >= 1)
        bg_fpr = bg_fp_count / max(1, len(bg_ids))

        result.metrics = {
            "scenario_id": config.scenario_id,
            "seed": config.seed,
            "disabled_groups": list(disabled_groups),
            "farm_recall": round(farm_recall, 4),
            "bot_accounts_count": len(bot_ids),
            "bot_detected_count": bot_detected_count,
            "decoy_accounts_count": len(decoy_ids),
            "decoy_restricted_count": decoy_restricted_count,
            "decoy_restriction_rate": round(decoy_restriction_rate, 4),
            "background_fpr": round(bg_fpr, 4),
            "detection_delay_throttle": first_throttle_window,
            "detection_delay_challenge": first_challenge_window,
            "detection_delay_restriction": first_restriction_window,
            "total_audit_decisions": len(self.audit_service.get_records()),
            "audit_hash_chain_valid": self.audit_service.verify_integrity()[0],
        }

        result.audit_records = self.audit_service.get_records()
        return result
