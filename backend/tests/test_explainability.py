import pytest
from backend.app.schemas.event import Account, Post
from backend.app.schemas.scoring import ClusterScoringResult, GateEvaluation, GroupEvidence, SignalEvidence
from backend.app.schemas.policy import ClusterPolicyDecision, AccountPolicyDecision, ResponseState
from backend.app.explainability.evidence_card import EvidenceCardGenerator
from backend.app.explainability.counterfactuals import CounterfactualEngine


def test_exact_additivity_and_counterfactuals():
    cf_engine = CounterfactualEngine()

    breakdown = {
        "Provenance": GroupEvidence(
            group_name="Provenance",
            raw_sum=2.5,
            capped_evidence=2.5,
            is_active=True,
            threshold=1.0,
        ),
        "Behavioral": GroupEvidence(
            group_name="Behavioral",
            raw_sum=2.0,
            capped_evidence=2.0,
            is_active=True,
            threshold=1.0,
        ),
        "Content": GroupEvidence(
            group_name="Content",
            raw_sum=2.2,
            capped_evidence=2.2,
            is_active=True,
            threshold=1.0,
        ),
    }

    # Running risk is 6.7, current state is Throttle (1)
    cf_outcomes = cf_engine.generate_counterfactuals(
        group_breakdown=breakdown,
        current_state=ResponseState.THROTTLE.value,
        running_risk=6.7,
        persistence_count=2,
        is_member_eligible=True,
    )

    assert len(cf_outcomes) == 3

    # Check Provenance counterfactual
    prov_cf = next(c for c in cf_outcomes if c.removed_group_or_signal == "Provenance")
    # Invariant I1: Without Provenance, it MUST drop to State 0 (Observe)!
    assert prov_cf.counterfactual_state == ResponseState.OBSERVE.value
    assert "strictly fails Invariant I1" in prov_cf.explanation
    assert prov_cf.delta_log_odds == 2.5


def test_decoy_explanation_card():
    generator = EvidenceCardGenerator()

    # Create mock decoy scoring: high Content, but NO Provenance
    gate_decoy = GateEvaluation(
        active_groups_count=1,
        active_groups=["Content"],
        has_active_provenance=False,
        gate_passed=False,
        gate_reason="Gate REFUSED: No active Provenance evidence group. Active groups: 1 (Content). Invariant I1 holds.",
        is_behavior_only=True,
    )
    scoring_decoy = ClusterScoringResult(
        cluster_id="decoy_fan_cluster",
        window_index=1,
        evidence_score_current=2.5,
        running_risk_score=2.5,
        group_breakdown={
            "Provenance": GroupEvidence(group_name="Provenance", raw_sum=0.0, capped_evidence=0.0, is_active=False, threshold=1.0),
            "Behavioral": GroupEvidence(group_name="Behavioral", raw_sum=0.4, capped_evidence=0.4, is_active=False, threshold=1.0),
            "Content": GroupEvidence(group_name="Content", raw_sum=2.5, capped_evidence=2.5, is_active=True, threshold=1.0),
        },
        gate=gate_decoy,
        coordination_score=2.9,
        member_count=25,
        eligible_count=0,
        ineligible_count=25,
    )

    policy_decoy = ClusterPolicyDecision(
        cluster_id="decoy_fan_cluster",
        window_index=1,
        median_state_eligible=0,
        overall_cluster_state=0,
        member_count=25,
        eligible_count=0,
        eligible_fraction=0.0,
        gate_passed=False,
        gate_reason=gate_decoy.gate_reason,
        rule_fired="Decoy protected by non-compensatory gate",
        member_decisions=[],
    )

    accounts = {
        f"fan_{i}": Account(account_id=f"fan_{i}", created_at=1750000000.0)
        for i in range(25)
    }

    card = generator.generate_card(
        cluster_id="decoy_fan_cluster",
        cluster_members=set(accounts.keys()),
        all_accounts=accounts,
        posts=[],
        scoring_res=scoring_decoy,
        policy_dec=policy_decoy,
    )

    assert card.current_state == 0
    assert card.gate_passed is False
    assert "No active Provenance evidence group" in card.gate_message
    assert "Provenance" in card.missing_groups
    assert card.has_provenance is False
