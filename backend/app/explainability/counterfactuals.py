"""
Counterfactual Re-Scoring Engine for BreachX / HYDRA.
Implements Section 11.2 and Invariant I4:
- Re-scores cluster with each evidence group removed.
- Re-evaluates non-compensatory gate and state machine.
- Additive nature of log-odds makes contributions exact.
"""

from typing import Dict, List, Any
from backend.app.schemas.scoring import GroupEvidence, GateEvaluation
from backend.app.schemas.explainability import CounterfactualOutcome
from backend.app.scoring.gate import EvidenceGate
from backend.app.policy.state_machine import ResponseLadderStateMachine


class CounterfactualEngine:
    """
    Computes exact counterfactual state transitions by systematically omitting evidence.
    """

    def __init__(self, state_machine: ResponseLadderStateMachine = None):
        self.state_machine = state_machine or ResponseLadderStateMachine()

    def generate_counterfactuals(
        self,
        group_breakdown: Dict[str, GroupEvidence],
        current_state: int,
        running_risk: float,
        persistence_count: int,
        is_member_eligible: bool = True,
    ) -> List[CounterfactualOutcome]:
        """
        Computes counterfactual outcomes for:
        1. Without Provenance
        2. Without Behavioral
        3. Without Content
        """
        outcomes: List[CounterfactualOutcome] = []
        evaluable_groups = ["Provenance", "Behavioral", "Content"]

        for grp_to_remove in evaluable_groups:
            if grp_to_remove not in group_breakdown:
                continue

            # Clone group breakdown with this group zeroed out
            modified_breakdown: Dict[str, GroupEvidence] = {}
            delta_score = 0.0

            for g_name, g_obj in group_breakdown.items():
                if g_name == grp_to_remove:
                    delta_score = g_obj.capped_evidence
                    modified_breakdown[g_name] = GroupEvidence(
                        group_name=g_name,
                        raw_sum=0.0,
                        capped_evidence=0.0,
                        is_active=False,
                        threshold=g_obj.threshold,
                        signals=[],
                    )
                else:
                    modified_breakdown[g_name] = g_obj

            # Re-evaluate gate
            new_gate = EvidenceGate.evaluate_gate(modified_breakdown)
            new_risk = max(0.0, running_risk - delta_score)

            # Re-evaluate state
            cf_state, cf_rule, _ = self.state_machine.compute_next_state(
                current_state=0,  # Re-evaluate from baseline to observe steady-state effect
                running_risk=new_risk,
                persistence_count=persistence_count,
                gate_passed=new_gate.gate_passed,
                is_member_eligible=is_member_eligible and (grp_to_remove != "Provenance"),
            )

            # Explain difference
            if grp_to_remove == "Provenance" and current_state > 0:
                explanation = f"Without {grp_to_remove} evidence, the cluster strictly fails Invariant I1 and remains at State 0 (Observe)."
            elif cf_state < current_state:
                explanation = f"Without {grp_to_remove} evidence, score drops by {delta_score:.2f} log-odds and response state drops from {current_state} to {cf_state}."
            elif not group_breakdown[grp_to_remove].is_active:
                explanation = f"Removing {grp_to_remove} evidence has no effect because this group was already inactive."
            else:
                explanation = f"Removing {grp_to_remove} evidence reduces score by {delta_score:.2f} log-odds but state remains {cf_state}."

            outcomes.append(
                CounterfactualOutcome(
                    removed_group_or_signal=grp_to_remove,
                    original_state=current_state,
                    counterfactual_state=cf_state,
                    delta_log_odds=round(delta_score, 4),
                    explanation=explanation,
                )
            )

        return outcomes
