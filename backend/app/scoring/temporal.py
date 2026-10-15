"""
Temporal Risk Accumulation, Decay, and State Persistence for BreachX / HYDRA.
Implements Sections 7.4, 8.2, 21.8, 21.14, and Invariant I3:
- Moving-average risk: R_c(t) = lambda * R_c(t-1) + (1 - lambda) * L_c(t).
- Coordination score C_c = capped(E_Behavioral) + capped(E_Content) for review queue.
- Reversibility: when evidence stops, risk decays towards zero.
- Per-account risk and persistence tracking (§21.14).
"""

from typing import Dict, List, Set, Optional, Tuple, Any
import numpy as np

DEFAULT_DECAY = 0.80  # Lambda for exponential moving average (§7.4)


class TemporalTracker:
    """
    Maintains running risk, persistence counters, and state per account/cluster across windows.
    """

    def __init__(self, decay: float = DEFAULT_DECAY):
        self.decay = decay
        # Account-level state tracking (Section 21.14 default)
        self.account_risk: Dict[str, float] = {}
        self.account_persistence: Dict[str, int] = {}
        self.account_state: Dict[str, int] = {}
        self.account_ttl: Dict[str, int] = {}  # Remaining TTL for restrictions

    def update_account_risk(
        self,
        account_id: str,
        cluster_evidence_l_c: float,
        is_gate_passed: bool,
    ) -> Tuple[float, int]:
        """
        Updates running risk and persistence for an individual account.
        """
        prev_risk = self.account_risk.get(account_id, 0.0)
        curr_risk = (self.decay * prev_risk) + ((1.0 - self.decay) * cluster_evidence_l_c)
        self.account_risk[account_id] = round(curr_risk, 4)

        # Persistence counts consecutive windows where gate passed and risk was elevated
        prev_persist = self.account_persistence.get(account_id, 0)
        if is_gate_passed and curr_risk >= 1.5:
            curr_persist = prev_persist + 1
        else:
            # Decay persistence
            curr_persist = max(0, prev_persist - 1)
        self.account_persistence[account_id] = curr_persist

        return self.account_risk[account_id], curr_persist

    def decay_inactive_accounts(self, active_account_ids: Set[str]) -> None:
        """
        Decays risk for accounts that were not part of any active cluster in this window (Invariant I3).
        """
        for aid in list(self.account_risk.keys()):
            if aid not in active_account_ids:
                old_risk = self.account_risk[aid]
                new_risk = self.decay * old_risk
                self.account_risk[aid] = round(new_risk, 4)
                self.account_persistence[aid] = max(0, self.account_persistence.get(aid, 0) - 1)
                # Decrement restriction TTL
                if self.account_ttl.get(aid, 0) > 0:
                    self.account_ttl[aid] -= 1
                    if self.account_ttl[aid] == 0 and self.account_state.get(aid, 0) == 3:
                        # TTL expired, restriction lifts!
                        self.account_state[aid] = 0

    @staticmethod
    def compute_coordination_score(group_breakdown: Dict[str, Any]) -> float:
        """
        Computes coordination score C_c = sum of capped Behavioral + Content (§21.8).
        Used to rank behavior-only clusters for the human review queue.
        """
        c_beh = group_breakdown.get("Behavioral").capped_evidence if "Behavioral" in group_breakdown else 0.0
        c_cnt = group_breakdown.get("Content").capped_evidence if "Content" in group_breakdown else 0.0
        return round(float(c_beh + c_cnt), 4)
