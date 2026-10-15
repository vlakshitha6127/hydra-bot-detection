"""
Scripted Attacker Schedule and Cost-of-Evasion Engine for BreachX / HYDRA.
Implements Milestone M8, Sections 10.1, 10.2, and 21.16:
- Scripted Tactic Schedule (Round 1: Naive, Round 2: Paraphrasing, Round 3: Timing Jitter, Round 4: Infrastructure Rotation).
- Strict observability boundary: attacker only observes defender actions (throttled/challenged/restricted counts),
  never detector scores or thresholds.
- Computes Primary axis: Throughput retained (posts delivered per account-hour vs unevaded campaign).
- Computes Secondary axes: Reach retained, distinct devices/IPs required.
"""

from typing import List, Dict, Tuple, Any
from backend.app.schemas.attacker import (
    AttackerTactics,
    DefenderObservation,
    CostOfEvasionRecord,
)


class ScriptedAttackerEngine:
    """
    Simulates multi-round attacker adaptation schedule (§10.1) and measures cost of evasion (§10.2).
    """

    def __init__(self, baseline_posts_per_hour: float = 80.0):
        self.baseline_posts_per_hour = baseline_posts_per_hour
        # Pre-defined scripted tactic schedule
        self.schedule: List[AttackerTactics] = [
            AttackerTactics(
                round_index=1,
                name="Round 1: Naive Coordinated Campaign",
                description="High-frequency burst posting, identical templates, 4 shared devices.",
                timing_jitter=0.05,
                paraphrase_rate=0.05,
                shared_devices_count=4,
                posting_rate_multiplier=1.0,
                signup_spread_days=0.05,
            ),
            AttackerTactics(
                round_index=2,
                name="Round 2: Content Paraphrasing",
                description="Attacker paraphrases messages to evade exact MinHash shingling; retains shared hardware.",
                timing_jitter=0.10,
                paraphrase_rate=0.85,
                shared_devices_count=4,
                posting_rate_multiplier=0.85,
                signup_spread_days=0.1,
            ),
            AttackerTactics(
                round_index=3,
                name="Round 3: Timing Jitter & Delay",
                description="Attacker adds random posting delays to break synchrony burst signals; throughput drops.",
                timing_jitter=0.65,
                paraphrase_rate=0.85,
                shared_devices_count=8,
                posting_rate_multiplier=0.60,
                signup_spread_days=1.0,
            ),
            AttackerTactics(
                round_index=4,
                name="Round 4: Full Infrastructure Rotation",
                description="Attacker eliminates shared hardware by rotating 40 distinct virtual devices and proxy IPs.",
                timing_jitter=0.75,
                paraphrase_rate=0.90,
                shared_devices_count=40,
                posting_rate_multiplier=0.35,
                signup_spread_days=7.0,
            ),
        ]

    def get_tactics_for_round(self, round_index: int) -> AttackerTactics:
        idx = max(0, min(len(self.schedule) - 1, round_index - 1))
        return self.schedule[idx]

    def compute_cost_of_evasion(
        self,
        round_index: int,
        observation: DefenderObservation,
    ) -> CostOfEvasionRecord:
        """
        Calculates cost-of-evasion metrics based on attacker tactics and defender actions.
        """
        tactics = self.get_tactics_for_round(round_index)

        # Primary Axis: Throughput Retained (§10.2)
        # Reduced by voluntary rate throttling and involuntary defender restrictions
        involuntary_drop = (
            (observation.restricted_count * 1.0)
            + (observation.challenged_count * 0.4)
            + (observation.throttled_count * 0.2)
        ) / max(1, observation.total_bot_accounts)

        effective_rate = tactics.posting_rate_multiplier * max(0.05, 1.0 - involuntary_drop)
        throughput_retained_pct = round(effective_rate * 100.0, 2)

        # Secondary Axes: Reach and Infrastructure resources (§10.2)
        reach_retained_pct = round(
            max(0.05, (1.0 - (observation.restricted_count / max(1, observation.total_bot_accounts))))
            * tactics.posting_rate_multiplier
            * 100.0,
            2,
        )

        distinct_devices = tactics.shared_devices_count
        distinct_ips = max(2, tactics.shared_devices_count // 2)

        summary = (
            f"Throttled: {observation.throttled_count}, "
            f"Challenged: {observation.challenged_count}, "
            f"Restricted: {observation.restricted_count}"
        )

        return CostOfEvasionRecord(
            round_index=round_index,
            tactic_name=tactics.name,
            throughput_retained_pct=throughput_retained_pct,
            reach_retained_pct=reach_retained_pct,
            distinct_devices_required=distinct_devices,
            distinct_ips_required=distinct_ips,
            escape_rate_pct=round(observation.escape_rate * 100.0, 2),
            detection_state_summary=summary,
        )
