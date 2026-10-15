import pytest
from backend.app.schemas.policy import ResponseState
from backend.app.policy.state_machine import ResponseLadderStateMachine
from backend.app.scoring.temporal import TemporalTracker
from backend.app.scoring.calibrator import EvidenceCalibrator
from backend.app.scoring.gate import EvidenceGate
from backend.app.audit.hasher import compute_record_hash, verify_hash_chain, GENESIS_HASH
from backend.app.core.security import hash_device_id, hash_ip_range


def test_i1_no_single_signal_or_unprovenanced_restriction():
    """
    Invariant I1: No restrictive action from a single signal.
    Policy engine strictly requires evidence from at least 2 evidence groups,
    one of which MUST be Provenance (Sections 7.3, 21.1).
    """
    calibrator = EvidenceCalibrator()

    # Case A: Only one signal firing in Content
    _, breakdown_single = calibrator.evaluate_cluster_evidence({
        "semantic_similarity": 0.99,
    })
    gate_single = EvidenceGate.evaluate_gate(breakdown_single)
    assert gate_single.gate_passed is False

    # Case B: Multiple signals firing in Content + Behavioral, but NO Provenance (e.g. viral news / fan wave)
    _, breakdown_behavior_only = calibrator.evaluate_cluster_evidence({
        "semantic_similarity": 0.99,
        "lexical_near_duplicates": 0.99,
        "interval_regularity": 0.99,
        "synchronized_bursts": 0.99,
    })
    gate_behavior_only = EvidenceGate.evaluate_gate(breakdown_behavior_only)
    assert gate_behavior_only.gate_passed is False
    assert gate_behavior_only.is_behavior_only is True

    # State machine must reject escalation to Throttle/Challenge/Restriction
    sm = ResponseLadderStateMachine()
    next_st, rule, _ = sm.compute_next_state(
        current_state=ResponseState.OBSERVE.value,
        running_risk=8.0,
        persistence_count=5,
        gate_passed=gate_behavior_only.gate_passed,
        is_member_eligible=True,
    )
    assert next_st == ResponseState.OBSERVE.value
    assert "RULE_GATE_UNMET" in rule


def test_i2_persistence_requirement():
    """
    Invariant I2: No restrictive action from a single time window.
    Requires persistence count >= N1 (Section 8.1).
    """
    sm = ResponseLadderStateMachine(n1=2)

    # In window 1 (persistence = 1), even if gate passed and risk is high
    next_st, rule, _ = sm.compute_next_state(
        current_state=ResponseState.OBSERVE.value,
        running_risk=4.5,
        persistence_count=1,  # Only 1 window!
        gate_passed=True,
        is_member_eligible=True,
    )
    # Must remain at Observe
    assert next_st == ResponseState.OBSERVE.value
    assert "RULE_REMAIN_OBSERVE" in rule

    # In window 2 (persistence = 2 >= N1)
    next_st2, rule2, _ = sm.compute_next_state(
        current_state=ResponseState.OBSERVE.value,
        running_risk=4.5,
        persistence_count=2,  # Persisted!
        gate_passed=True,
        is_member_eligible=True,
    )
    assert next_st2 == ResponseState.THROTTLE.value


def test_i3_ttl_and_decay_reversibility():
    """
    Invariant I3: All automated actions are reversible.
    Restrictions carry a TTL; risk decays without fresh evidence.
    """
    tracker = TemporalTracker(decay=0.8)
    aid = "test_user_reversibility"

    # Start with high risk and restriction
    tracker.account_risk[aid] = 6.0
    tracker.account_state[aid] = ResponseState.RESTRICTION.value
    tracker.account_ttl[aid] = 2

    # Window passes with no active evidence for this account
    tracker.decay_inactive_accounts(active_account_ids=set())

    # Risk decayed
    assert tracker.account_risk[aid] == 4.8  # 6.0 * 0.8
    assert tracker.account_ttl[aid] == 1
    assert tracker.account_state[aid] == ResponseState.RESTRICTION.value

    # Second window passes without evidence
    tracker.decay_inactive_accounts(active_account_ids=set())

    # TTL reaches zero -> restriction lifts!
    assert tracker.account_ttl[aid] == 0
    assert tracker.account_state[aid] == ResponseState.OBSERVE.value
    assert tracker.account_risk[aid] == 3.84


def test_i6_no_automated_permanent_action():
    """
    Invariant I6: Permanent decisions are human-only.
    System cannot self-apply permanent action; State 4 is human escalation.
    """
    sm = ResponseLadderStateMachine()

    # Even with max risk and maximum persistence, state machine caps at State 4
    next_st, rule, _ = sm.compute_next_state(
        current_state=ResponseState.RESTRICTION.value,
        running_risk=100.0,
        persistence_count=99,
        gate_passed=True,
        is_member_eligible=True,
    )
    assert next_st == ResponseState.ESCALATION.value
    assert "RULE_ESCALATE_TO_HUMAN" in rule

    # Once at State 4, cannot escalate any further automatically
    next_st2, rule2, _ = sm.compute_next_state(
        current_state=ResponseState.ESCALATION.value,
        running_risk=100.0,
        persistence_count=100,
        gate_passed=True,
        is_member_eligible=True,
    )
    assert next_st2 == ResponseState.ESCALATION.value
    assert "HUMAN_CEILING" in rule2
