import pytest
from backend.app.schemas.event import Account
from backend.app.schemas.scoring import ClusterScoringResult, GateEvaluation, GroupEvidence
from backend.app.schemas.policy import ResponseState
from backend.app.policy.state_machine import ResponseLadderStateMachine
from backend.app.policy.engine import PolicyEngine
from backend.app.audit.log import AuditLogService
from backend.app.scoring.temporal import TemporalTracker


def test_no_state_skipping_in_state_machine():
    sm = ResponseLadderStateMachine(t1=2.0, t2=3.5, t3=5.0, n1=2, n2=3, n3=4)

    # From State 0 (Observe), even with extreme risk 10.0 and persistence 5,
    # the state machine MUST NOT jump straight to Restriction (State 3).
    # It must transition to Throttle (State 1) first!
    next_st, rule, ttl = sm.compute_next_state(
        current_state=ResponseState.OBSERVE.value,
        running_risk=10.0,
        persistence_count=5,
        gate_passed=True,
        is_member_eligible=True,
    )
    assert next_st == ResponseState.THROTTLE.value
    assert "ESCALATE_TO_THROTTLE" in rule

    # Next step from Throttle with extreme risk -> moves to Challenge (State 2)
    next_st2, rule2, ttl2 = sm.compute_next_state(
        current_state=ResponseState.THROTTLE.value,
        running_risk=10.0,
        persistence_count=5,
        gate_passed=True,
        is_member_eligible=True,
    )
    assert next_st2 == ResponseState.CHALLENGE.value

    # Next step from Challenge -> moves to Restriction (State 3)
    next_st3, rule3, ttl3 = sm.compute_next_state(
        current_state=ResponseState.CHALLENGE.value,
        running_risk=10.0,
        persistence_count=5,
        gate_passed=True,
        is_member_eligible=True,
    )
    assert next_st3 == ResponseState.RESTRICTION.value
    assert ttl3 > 0


def test_eligible_member_rule_and_test_case():
    """
    Authoritative Eligible-Member Test (§21.14):
    A 40-account farm in which 15 accounts have shared-device links shows the cluster
    at the eligible members' state, an eligible fraction of 15/40, and the other
    25 accounts at Observe plus review flag.
    """
    audit = AuditLogService()
    policy = PolicyEngine(audit_service=audit)

    accounts: dict[str, Account] = {}
    cluster_member_ids = set()

    # 15 accounts sharing a device fingerprint
    for i in range(15):
        aid = f"farm_linked_{i}"
        accounts[aid] = Account(
            account_id=aid,
            created_at=1776300000.0,
            device_hash="dev_shared_cluster_hardware",
            ip_range_hash="ip_shared_block",
        )
        cluster_member_ids.add(aid)

    # 25 accounts with independent unique hardware (no shared device in cluster)
    for i in range(25):
        aid = f"farm_unlinked_{i}"
        accounts[aid] = Account(
            account_id=aid,
            created_at=1776300000.0,
            device_hash=f"dev_isolated_hardware_{i}",
            ip_range_hash=f"ip_isolated_block_{i}",
        )
        cluster_member_ids.add(aid)

    # Simulate high cluster evidence and passed gate
    mock_gate = GateEvaluation(
        active_groups_count=3,
        active_groups=["Provenance", "Behavioral", "Content"],
        has_active_provenance=True,
        gate_passed=True,
        gate_reason="Gate passed",
        is_behavior_only=False,
    )
    mock_scoring = ClusterScoringResult(
        cluster_id="cluster_farm_mixed_eligibility",
        window_index=1,
        evidence_score_current=6.0,
        running_risk_score=6.0,
        group_breakdown={},
        gate=mock_gate,
        coordination_score=4.0,
        member_count=40,
        eligible_count=15,
        ineligible_count=25,
    )

    # Prime persistence to simulate 2 consecutive windows so eligible members escalate to Throttle
    for aid in cluster_member_ids:
        policy.temporal_tracker.account_persistence[aid] = 2
        policy.temporal_tracker.account_risk[aid] = 4.0

    cluster_dec = policy.execute_policy(
        cluster_id="cluster_farm_mixed_eligibility",
        window_index=2,
        cluster_member_ids=cluster_member_ids,
        all_accounts=accounts,
        scoring_result=mock_scoring,
    )

    # Verify authoritative requirements:
    # 1. Eligible fraction is 15/40 (0.375)
    assert cluster_dec.eligible_count == 15
    assert cluster_dec.member_count == 40
    assert cluster_dec.eligible_fraction == 0.375

    # 2. 15 eligible accounts escalated to Throttle (State 1)
    for dec in cluster_dec.member_decisions:
        if dec.account_id.startswith("farm_linked_"):
            assert dec.is_eligible is True
            assert dec.new_state == ResponseState.THROTTLE.value
        else:
            # 3. The other 25 accounts remain at Observe (State 0) with review flag
            assert dec.is_eligible is False
            assert dec.new_state == ResponseState.OBSERVE.value
            assert "RULE_INELIGIBLE_MEMBER" in dec.rule_fired


def test_mixed_cluster_test():
    """
    Authoritative Mixed-Cluster Test (§21.14):
    A cluster of bot accounts and legitimate accounts joined only by content or timing links.
    Only accounts with their own provenance link are eligible, and no legitimate account
    is acted on because of a bot member's provenance.
    """
    audit = AuditLogService()
    policy = PolicyEngine(audit_service=audit)

    accounts: dict[str, Account] = {}
    cluster_member_ids = set()

    # 10 Bot accounts sharing a device
    for i in range(10):
        aid = f"bot_{i}"
        accounts[aid] = Account(
            account_id=aid,
            created_at=1776300000.0,
            device_hash="dev_bot_farm_rig",
            ip_range_hash="ip_bot_proxy",
        )
        cluster_member_ids.add(aid)

    # 10 Legitimate accounts with diverse devices and IPs (joined e.g. by trending hashtag)
    for i in range(10):
        aid = f"innocent_fan_{i}"
        accounts[aid] = Account(
            account_id=aid,
            created_at=1750000000.0,
            device_hash=f"dev_phone_{i}",
            ip_range_hash=f"ip_home_dsl_{i}",
        )
        cluster_member_ids.add(aid)

    mock_gate = GateEvaluation(
        active_groups_count=2,
        active_groups=["Provenance", "Content"],
        has_active_provenance=True,
        gate_passed=True,
        gate_reason="Gate passed on bot provenance",
        is_behavior_only=False,
    )
    mock_scoring = ClusterScoringResult(
        cluster_id="mixed_community_cluster",
        window_index=1,
        evidence_score_current=5.0,
        running_risk_score=5.0,
        group_breakdown={},
        gate=mock_gate,
        coordination_score=2.0,
        member_count=20,
        eligible_count=10,
        ineligible_count=10,
    )

    # Prime persistence
    for aid in cluster_member_ids:
        policy.temporal_tracker.account_persistence[aid] = 2
        policy.temporal_tracker.account_risk[aid] = 4.0

    cluster_dec = policy.execute_policy(
        cluster_id="mixed_community_cluster",
        window_index=2,
        cluster_member_ids=cluster_member_ids,
        all_accounts=accounts,
        scoring_result=mock_scoring,
    )

    # Invariant: No legitimate innocent account is acted on because of a bot member's provenance!
    for dec in cluster_dec.member_decisions:
        if dec.account_id.startswith("innocent_fan_"):
            assert dec.is_eligible is False
            assert dec.new_state == ResponseState.OBSERVE.value
            assert "RULE_INELIGIBLE_MEMBER" in dec.rule_fired
        elif dec.account_id.startswith("bot_"):
            assert dec.is_eligible is True
            assert dec.new_state == ResponseState.THROTTLE.value
