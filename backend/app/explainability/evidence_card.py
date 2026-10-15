"""
Evidence Card Generator for BreachX / HYDRA.
Implements Milestone M6, Sections 11, 20.5, and 21.1:
- Generates detailed evidence cards for clusters (bot farm and legitimate decoys).
- Decoy explanation moment: explains why suspicious-looking decoys (fan community / news feeds)
  are safely refused from automated action.
- Exact additive signal breakdown and counterfactuals.
- Representative evidence: anonymized device groups, near-duplicate post text snippets.
"""

from typing import List, Dict, Set, Optional, Any
import numpy as np

from backend.app.schemas.event import Account, Post, Interaction
from backend.app.schemas.scoring import ClusterScoringResult
from backend.app.schemas.policy import ClusterPolicyDecision, ResponseState
from backend.app.schemas.explainability import (
    EvidenceCard,
    RepresentativeSample,
    CounterfactualOutcome,
)
from backend.app.explainability.counterfactuals import CounterfactualEngine
from backend.app.core.security import truncate_hash


STATE_LABELS = {
    0: "State 0: Observe (No Impact)",
    1: "State 1: Throttle (Mild Rate Limit)",
    2: "State 2: Verification Challenge",
    3: "State 3: Temporary Restriction (TTL)",
    4: "State 4: Human Escalation",
}


class EvidenceCardGenerator:
    """
    Constructs explainability evidence cards.
    """

    def __init__(self):
        self.cf_engine = CounterfactualEngine()

    def generate_card(
        self,
        cluster_id: str,
        cluster_members: Set[str],
        all_accounts: Dict[str, Account],
        posts: List[Post],
        scoring_res: ClusterScoringResult,
        policy_dec: ClusterPolicyDecision,
    ) -> EvidenceCard:
        """
        Builds full structured EvidenceCard.
        """
        accounts = [all_accounts[aid] for aid in cluster_members if aid in all_accounts]
        cluster_posts = [p for p in posts if p.account_id in cluster_members]

        # 1. Creation time span
        if accounts:
            c_times = [a.created_at for a in accounts]
            time_span = max(c_times) - min(c_times)
        else:
            time_span = 0.0

        # 2. Risk trend
        if scoring_res.running_risk_score > scoring_res.evidence_score_current + 0.5:
            trend = "decaying"
        elif scoring_res.running_risk_score < scoring_res.evidence_score_current - 0.5:
            trend = "increasing"
        else:
            trend = "steady"

        # 3. Signal contributions and Group contributions
        group_contribs: Dict[str, float] = {}
        flat_signals: List[Dict[str, Any]] = []

        for g_name, grp in scoring_res.group_breakdown.items():
            group_contribs[g_name] = grp.capped_evidence
            for s in grp.signals:
                flat_signals.append({
                    "signal_name": s.signal_name,
                    "family": s.family,
                    "group": s.group,
                    "raw_value": s.raw_value,
                    "calibrated_log_odds": s.log_odds_contribution,
                    "weight": s.weight,
                })

        # 4. Gate status
        all_groups = ["Provenance", "Behavioral", "Content"]
        active = scoring_res.gate.active_groups
        missing = [g for g in all_groups if g not in active]

        # 5. Counterfactuals (§11.2)
        counterfactuals = self.cf_engine.generate_counterfactuals(
            group_breakdown=scoring_res.group_breakdown,
            current_state=policy_dec.overall_cluster_state,
            running_risk=scoring_res.running_risk_score,
            persistence_count=2,
            is_member_eligible=(policy_dec.eligible_count > 0),
        )

        # 6. Representative evidence samples
        samples: List[RepresentativeSample] = []

        # Shared device sample (Invariant I8: hashes only)
        device_map: Dict[str, List[str]] = {}
        for a in accounts:
            if a.device_hash:
                device_map.setdefault(a.device_hash, []).append(a.account_id)

        shared_devs = {d: m for d, m in device_map.items() if len(m) > 1}
        if shared_devs:
            dev_hash, members = next(iter(shared_devs.items()))
            samples.append(
                RepresentativeSample(
                    sample_type="device_group",
                    description=f"{len(members)} accounts share hardware fingerprint {truncate_hash(dev_hash)}",
                    evidence_data={
                        "device_hash_prefix": truncate_hash(dev_hash),
                        "member_count": len(members),
                        "sample_members": members[:5],
                    },
                )
            )

        # Near-duplicate text sample
        if len(cluster_posts) >= 2:
            p1 = cluster_posts[0]
            p2 = cluster_posts[1]
            samples.append(
                RepresentativeSample(
                    sample_type="post_pair",
                    description="Coordinated message duplication sample",
                    evidence_data={
                        "post_1": {"account_id": p1.account_id, "text": p1.text[:120]},
                        "post_2": {"account_id": p2.account_id, "text": p2.text[:120]},
                    },
                )
            )

        # 7. Ineligible members list
        ineligible = [
            m.account_id for m in policy_dec.member_decisions if not m.is_eligible
        ]

        return EvidenceCard(
            cluster_id=cluster_id,
            window_index=scoring_res.window_index,
            member_count=policy_dec.member_count,
            eligible_count=policy_dec.eligible_count,
            eligible_fraction=policy_dec.eligible_fraction,
            creation_time_span_seconds=round(time_span, 1),
            current_state=policy_dec.overall_cluster_state,
            state_label=STATE_LABELS.get(policy_dec.overall_cluster_state, "State 0: Observe"),
            risk_trend=trend,
            running_risk=scoring_res.running_risk_score,
            evidence_score=scoring_res.evidence_score_current,
            group_contributions=group_contribs,
            signal_contributions=flat_signals,
            active_groups=active,
            missing_groups=missing,
            has_provenance=scoring_res.gate.has_active_provenance,
            gate_passed=scoring_res.gate.gate_passed,
            gate_message=scoring_res.gate.gate_reason,
            counterfactuals=counterfactuals,
            representative_samples=samples,
            ineligible_members=ineligible,
        )
