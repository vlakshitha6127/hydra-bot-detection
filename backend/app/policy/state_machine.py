"""
Graduated Response State Machine for BreachX / HYDRA.
Implements Sections 8.1, 8.2, 21.1, and Invariants I1, I2, I3, I6:
- State 0: Observe
- State 1: Throttle
- State 2: Verification Challenge
- State 3: Temporary Restriction (TTL)
- State 4: Human Escalation
Strictly enforces:
- No state skipping (0 cannot jump to 2 or 3).
- Strict non-compensatory gate + member-level eligibility for user-impacting states (1-3).
- Hysteresis de-escalation.
- TTL expiry on restrictions.
- Permanent action is human-only (Invariant I6).
"""

from typing import Tuple, Optional
from backend.app.schemas.policy import ResponseState

# Default tuned thresholds (§8.1, §21.10)
T1_THROTTLE = 2.0
T2_CHALLENGE = 3.5
T3_RESTRICTION = 5.0

# Persistence requirements (consecutive windows)
N1_PERSISTENCE = 2
N2_PERSISTENCE = 3
N3_PERSISTENCE = 4

# Hysteresis offset
HYSTERESIS_DELTA = 0.5
RESTRICTION_TTL_DEFAULT = 3


class ResponseLadderStateMachine:
    """
    Manages graduated response transitions for individual accounts.
    """

    def __init__(
        self,
        t1: float = T1_THROTTLE,
        t2: float = T2_CHALLENGE,
        t3: float = T3_RESTRICTION,
        n1: int = N1_PERSISTENCE,
        n2: int = N2_PERSISTENCE,
        n3: int = N3_PERSISTENCE,
        ttl_default: int = RESTRICTION_TTL_DEFAULT,
    ):
        self.t1 = t1
        self.t2 = t2
        self.t3 = t3
        self.n1 = n1
        self.n2 = n2
        self.n3 = n3
        self.ttl_default = ttl_default

    def compute_next_state(
        self,
        current_state: int,
        running_risk: float,
        persistence_count: int,
        gate_passed: bool,
        is_member_eligible: bool,
        current_ttl: int = 0,
    ) -> Tuple[int, str, int]:
        """
        Computes (new_state, rule_fired, new_ttl).
        Enforces one-step-at-a-time transitions, hysteresis, and eligibility.
        """
        # If account is ineligible (no personal provenance link), it CANNOT receive user-impacting action (States 1-3)
        # Stays at State 0 with a review flag (§21.12, §21.14)
        if not is_member_eligible:
            return (
                ResponseState.OBSERVE.value,
                "RULE_INELIGIBLE_MEMBER: Account lacks direct provenance link; held at Observe with review flag.",
                0,
            )

        # If gate failed (e.g. no provenance at cluster level), cannot escalate to user-impacting states
        if not gate_passed:
            # Check de-escalation if previously restricted
            if current_state > ResponseState.OBSERVE.value:
                # One step de-escalation
                new_st = max(0, current_state - 1)
                return (
                    new_st,
                    "RULE_DE_ESCALATE_GATE_FAILED: Gate requirement unmet; de-escalating one step.",
                    0,
                )
            return (
                ResponseState.OBSERVE.value,
                "RULE_GATE_UNMET: Cluster failed evidence gate; held at Observe.",
                0,
            )

        # --- ESCALATION LOGIC (One step at a time, no state skipping) ---

        # Candidate target based on risk and persistence
        if current_state == ResponseState.OBSERVE.value:
            if running_risk >= self.t1 and persistence_count >= self.n1:
                return (
                    ResponseState.THROTTLE.value,
                    f"RULE_ESCALATE_TO_THROTTLE: Risk {running_risk:.2f} >= T1 ({self.t1}) and persistence {persistence_count} >= N1 ({self.n1}).",
                    0,
                )
            return (
                ResponseState.OBSERVE.value,
                f"RULE_REMAIN_OBSERVE: Risk {running_risk:.2f} or persistence {persistence_count} below Throttle requirements.",
                0,
            )

        elif current_state == ResponseState.THROTTLE.value:
            # De-escalation with hysteresis
            if running_risk < (self.t1 - HYSTERESIS_DELTA):
                return (
                    ResponseState.OBSERVE.value,
                    f"RULE_HYSTERESIS_DE_ESCALATE: Risk {running_risk:.2f} dropped below T1 exit threshold ({self.t1 - HYSTERESIS_DELTA}).",
                    0,
                )
            # Escalation to Challenge (must already be in Throttle)
            if running_risk >= self.t2 and persistence_count >= self.n2:
                return (
                    ResponseState.CHALLENGE.value,
                    f"RULE_ESCALATE_TO_CHALLENGE: Risk {running_risk:.2f} >= T2 ({self.t2}) and persistence {persistence_count} >= N2 ({self.n2}).",
                    0,
                )
            return (
                ResponseState.THROTTLE.value,
                "RULE_MAINTAIN_THROTTLE: Conditions met to maintain mild rate limit.",
                0,
            )

        elif current_state == ResponseState.CHALLENGE.value:
            # De-escalation with hysteresis
            if running_risk < (self.t2 - HYSTERESIS_DELTA):
                return (
                    ResponseState.THROTTLE.value,
                    f"RULE_HYSTERESIS_DE_ESCALATE: Risk {running_risk:.2f} dropped below T2 exit threshold ({self.t2 - HYSTERESIS_DELTA}).",
                    0,
                )
            # Escalation to Temporary Restriction (must already be in Challenge)
            if running_risk >= self.t3 and persistence_count >= self.n3:
                return (
                    ResponseState.RESTRICTION.value,
                    f"RULE_ESCALATE_TO_RESTRICTION: Risk {running_risk:.2f} >= T3 ({self.t3}) and persistence {persistence_count} >= N3 ({self.n3}).",
                    self.ttl_default,
                )
            return (
                ResponseState.CHALLENGE.value,
                "RULE_MAINTAIN_CHALLENGE: Active verification challenge required.",
                0,
            )

        elif current_state == ResponseState.RESTRICTION.value:
            # TTL check
            if current_ttl <= 1 and running_risk < self.t3:
                return (
                    ResponseState.CHALLENGE.value,
                    "RULE_TTL_EXPIRED: Restriction TTL elapsed without sustained high evidence; reverting to Challenge.",
                    0,
                )
            # Escalation to Human Escalation (State 4)
            if running_risk >= self.t3 and persistence_count >= (self.n3 + 2):
                return (
                    ResponseState.ESCALATION.value,
                    "RULE_ESCALATE_TO_HUMAN: Sustained extreme risk under restriction; flagged for human analyst.",
                    0,
                )
            return (
                ResponseState.RESTRICTION.value,
                f"RULE_MAINTAIN_RESTRICTION: Active restriction (TTL remaining: {max(1, current_ttl)}).",
                max(0, current_ttl - 1),
            )

        elif current_state == ResponseState.ESCALATION.value:
            # Permanent ceiling for automation (Invariant I6)
            return (
                ResponseState.ESCALATION.value,
                "RULE_HUMAN_CEILING: Account at Human Escalation. Automated system cannot self-apply permanent action.",
                0,
            )

        return ResponseState.OBSERVE.value, "RULE_DEFAULT_OBSERVE", 0
