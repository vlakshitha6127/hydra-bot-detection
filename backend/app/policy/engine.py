"""
Authoritative Policy Engine for BreachX / HYDRA.
Implements Milestone M5, Sections 8, 21.1, 21.12, 21.14, and Invariants I1-I6:
- Member-level provenance eligibility (§21.12): account itself must have direct provenance link to another member.
- Cluster state = median state over eligible members (§21.14).
- Ineligible members stay at State 0 (Observe) with a review flag.
- One step at a time, no state skipping.
- Cryptographically logged decisions via hash-chained audit service.
"""

import time
from typing import Dict, List, Set, Tuple, Optional
import numpy as np

from backend.app.schemas.event import Account
from backend.app.schemas.scoring import ClusterScoringResult
from backend.app.schemas.policy import (
    ResponseState,
    AccountPolicyDecision,
    ClusterPolicyDecision,
)
from backend.app.policy.state_machine import ResponseLadderStateMachine
from backend.app.scoring.temporal import TemporalTracker
from backend.app.audit.log import AuditLogService


class PolicyEngine:
    """
    Coordinates cluster scoring, member-level eligibility, state progression, and audit logging.
    """

    def __init__(
        self,
        audit_service: AuditLogService,
        state_machine: Optional[ResponseLadderStateMachine] = None,
        temporal_tracker: Optional[TemporalTracker] = None,
    ):
        self.audit_service = audit_service
        self.state_machine = state_machine or ResponseLadderStateMachine()
        self.temporal_tracker = temporal_tracker or TemporalTracker()

    def check_member_eligibility(
        self,
        account: Account,
        cluster_accounts: List[Account],
        global_accounts: Dict[str, Account],
    ) -> Tuple[bool, str]:
        """
        Authoritative Member-Level Eligibility Rule (§21.12, §21.14):
        An account must have its own direct qualifying provenance link (shared device
        or rare shared-IP edge) to another cluster member to be eligible for states 1-3.
        Otherwise it stays at Observe with a review flag.
        """
        if not account.device_hash and not account.ip_range_hash:
            return False, "INELIGIBLE: Account has neither device fingerprint nor IP range."

        # Check for direct shared-device link to another member in the cluster
        if account.device_hash:
            for other in cluster_accounts:
                if other.account_id != account.account_id and other.device_hash == account.device_hash:
                    return True, "ELIGIBLE: Account shares hardware device with another cluster member."

        # Check for rare shared-IP link (popularity down-weighted)
        if account.ip_range_hash:
            # Check global popularity of this IP
            ip_glob_count = sum(
                1 for acc in global_accounts.values() if acc.ip_range_hash == account.ip_range_hash
            )
            # Rarity threshold: only small, rare shared subnets count as provenance links (e.g. <= 6 accounts)
            if ip_glob_count <= 6:
                for other in cluster_accounts:
                    if other.account_id != account.account_id and other.ip_range_hash == account.ip_range_hash:
                        return True, f"ELIGIBLE: Account shares rare IP subnet ({ip_glob_count} global hosts) with another member."

        return (
            False,
            "INELIGIBLE: No intra-cluster device link and IP subnet is either unique or a popular NAT. Remains at Observe with review flag.",
        )

    def execute_policy(
        self,
        cluster_id: str,
        window_index: int,
        cluster_member_ids: Set[str],
        all_accounts: Dict[str, Account],
        scoring_result: ClusterScoringResult,
    ) -> ClusterPolicyDecision:
        """
        Executes graduated policy decisions for a detected cluster.
        """
        cluster_accounts = [all_accounts[aid] for aid in cluster_member_ids if aid in all_accounts]
        gate_passed = scoring_result.gate.gate_passed
        cluster_l_c = scoring_result.evidence_score_current

        member_decisions: List[AccountPolicyDecision] = []
        eligible_member_states: List[int] = []
        eligible_count = 0
        ineligible_count = 0

        # Evaluate each member individually (§21.14)
        for acc in cluster_accounts:
            aid = acc.account_id
            # 1. Check member eligibility
            is_eligible, elig_reason = self.check_member_eligibility(
                acc, cluster_accounts, all_accounts
            )

            # 2. Update temporal running risk and persistence
            curr_risk, persist_cnt = self.temporal_tracker.update_account_risk(
                aid, cluster_l_c, gate_passed
            )

            # 3. Compute state transition
            prev_state = self.temporal_tracker.account_state.get(aid, ResponseState.OBSERVE.value)
            curr_ttl = self.temporal_tracker.account_ttl.get(aid, 0)

            new_state, rule_fired, new_ttl = self.state_machine.compute_next_state(
                current_state=prev_state,
                running_risk=curr_risk,
                persistence_count=persist_cnt,
                gate_passed=gate_passed,
                is_member_eligible=is_eligible,
                current_ttl=curr_ttl,
            )

            # Update tracking state
            self.temporal_tracker.account_state[aid] = new_state
            self.temporal_tracker.account_ttl[aid] = new_ttl

            if is_eligible:
                eligible_count += 1
                eligible_member_states.append(new_state)
            else:
                ineligible_count += 1

            dec = AccountPolicyDecision(
                account_id=aid,
                cluster_id=cluster_id,
                window_index=window_index,
                prev_state=prev_state,
                new_state=new_state,
                rule_fired=rule_fired,
                is_eligible=is_eligible,
                eligibility_reason=elig_reason,
                evidence_score=cluster_l_c,
                running_risk=curr_risk,
                persistence_count=persist_cnt,
                active_groups=scoring_result.gate.active_groups,
                has_provenance=scoring_result.gate.has_active_provenance,
                ttl_remaining=new_ttl,
            )
            member_decisions.append(dec)

            # 4. Append decision to tamper-evident audit log (Milestone M14a, Invariant I5, I7)
            self.audit_service.append_decision(
                {
                    "window_index": window_index,
                    "cluster_id": cluster_id,
                    "account_id": aid,
                    "prev_state": prev_state,
                    "new_state": new_state,
                    "rule_fired": rule_fired,
                    "evidence_score": cluster_l_c,
                    "running_risk": curr_risk,
                    "is_eligible": is_eligible,
                    "active_groups": scoring_result.gate.active_groups,
                    "timestamp": time.time(),
                }
            )

        # Cluster state shown is median of its eligible members (§21.14)
        if eligible_member_states:
            median_state = int(np.median(eligible_member_states))
        else:
            median_state = ResponseState.OBSERVE.value

        total_members = len(cluster_accounts)
        eligible_fraction = round(eligible_count / max(1, total_members), 4)

        cluster_decision = ClusterPolicyDecision(
            cluster_id=cluster_id,
            window_index=window_index,
            median_state_eligible=median_state,
            overall_cluster_state=median_state,
            member_count=total_members,
            eligible_count=eligible_count,
            eligible_fraction=eligible_fraction,
            gate_passed=gate_passed,
            gate_reason=scoring_result.gate.gate_reason,
            rule_fired=f"Cluster state {median_state} evaluated from {eligible_count}/{total_members} eligible members.",
            member_decisions=member_decisions,
        )

        return cluster_decision
