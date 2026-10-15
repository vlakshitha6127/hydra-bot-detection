import pytest
from backend.app.schemas.attacker import DefenderObservation
from backend.app.simulator.attacker import ScriptedAttackerEngine


def test_scripted_schedule_and_cost_of_evasion():
    engine = ScriptedAttackerEngine()

    # Round 1: Naive campaign heavily restricted by defender
    obs_r1 = DefenderObservation(
        round_index=1,
        total_bot_accounts=40,
        throttled_count=5,
        challenged_count=10,
        restricted_count=25,
        unrestricted_count=0,
        escape_rate=0.0,
    )
    cost_r1 = engine.compute_cost_of_evasion(1, obs_r1)

    assert cost_r1.throughput_retained_pct < 50.0  # Heavy restriction cuts throughput
    assert cost_r1.distinct_devices_required == 4

    # Round 4: Infrastructure rotation (40 devices) with slow posting
    obs_r4 = DefenderObservation(
        round_index=4,
        total_bot_accounts=40,
        throttled_count=0,
        challenged_count=0,
        restricted_count=0,
        unrestricted_count=40,
        escape_rate=1.0,  # Successfully escaped automated restriction
    )
    cost_r4 = engine.compute_cost_of_evasion(4, obs_r4)

    # Cost of evasion: Attacker escaped automated restrictions, BUT their voluntary throughput is only 35%!
    # And they had to buy 40 distinct devices instead of 4!
    assert cost_r4.distinct_devices_required == 40
    assert cost_r4.throughput_retained_pct <= 35.0
    assert cost_r4.escape_rate_pct == 100.0


def test_observability_boundary():
    # Attacker only accepts defender observations (actions count), no internal detector scores
    engine = ScriptedAttackerEngine()
    t = engine.get_tactics_for_round(2)
    assert t.round_index == 2
    assert "Paraphrasing" in t.name
