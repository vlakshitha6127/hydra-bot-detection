"""
Non-Compensatory Evidence Gate for BreachX / HYDRA.
Implements Sections 7.3, 21.1, 21.12, and Invariant I1:
- Restrictive automated states 1-3 strictly require A_c >= 2 active groups, ONE of which MUST be Provenance.
- Behavior-only clusters (Behavioral and/or Content, no Provenance) stay at State 0 (Observe)
  and route to the rate-limited review queue (§21.8).
- Clear, auditable gate pass/fail explanation messages.
"""

from typing import Dict, List, Tuple
from backend.app.schemas.scoring import GroupEvidence, GateEvaluation


class EvidenceGate:
    """
    Evaluates evidence group activation and provenance requirement.
    """

    @staticmethod
    def evaluate_gate(group_breakdown: Dict[str, GroupEvidence]) -> GateEvaluation:
        """
        Applies authoritative non-compensatory gate (§21.1).
        """
        active_groups = [
            grp.group_name
            for name, grp in group_breakdown.items()
            if grp.is_active and name != "Context"
        ]
        active_count = len(active_groups)
        has_provenance = group_breakdown.get("Provenance", False) and group_breakdown["Provenance"].is_active

        is_behavior_only = (
            active_count >= 1
            and not has_provenance
            and any(g in ("Behavioral", "Content") for g in active_groups)
        )

        # Gate Rule (§21.1): A_c >= 2 AND active Provenance
        if active_count >= 2 and has_provenance:
            gate_passed = True
            gate_reason = (
                f"Gate PASSED: {active_count} active evidence groups ({', '.join(active_groups)}), "
                f"including required Provenance group."
            )
        elif is_behavior_only:
            gate_passed = False
            gate_reason = (
                f"Gate REFUSED (Behavior-Only): Active groups ({', '.join(active_groups)}) lack required "
                f"Provenance evidence. Automated user-impacting action blocked; routed to Human Review Queue."
            )
        elif not has_provenance:
            gate_passed = False
            gate_reason = (
                f"Gate REFUSED: No active Provenance evidence group. "
                f"Active groups: {active_count} ({', '.join(active_groups) or 'none'}). Invariant I1 holds."
            )
        else:
            gate_passed = False
            gate_reason = (
                f"Gate REFUSED: Insufficient active evidence groups (count: {active_count} < 2). "
                f"Requires at least 2 independent active groups. Invariant I1 holds."
            )

        return GateEvaluation(
            active_groups_count=active_count,
            active_groups=active_groups,
            has_active_provenance=has_provenance,
            gate_passed=gate_passed,
            gate_reason=gate_reason,
            is_behavior_only=is_behavior_only,
        )
