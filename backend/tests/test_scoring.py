import pytest
from backend.app.scoring.calibrator import EvidenceCalibrator, E_MAX
from backend.app.scoring.gate import EvidenceGate
from backend.app.scoring.correlation import CorrelationAnalyzer


def test_scoring_calibration_and_exact_additivity():
    calibrator = EvidenceCalibrator(e_max=5.0)

    raw_signals = {
        "shared_device": 0.95,
        "creation_burst": 0.92,
        "synchronized_bursts": 0.96,
        "semantic_similarity": 0.94,
    }

    # Signal calibration
    l_c, breakdown = calibrator.evaluate_cluster_evidence(raw_signals)

    # Invariant I4: exact additivity in log-odds
    expected_sum = sum(
        grp.capped_evidence for name, grp in breakdown.items() if name != "Context"
    )
    assert round(l_c, 4) == round(expected_sum, 4)
    assert l_c > 0.0


def test_group_capping():
    calibrator = EvidenceCalibrator(e_max=3.0)  # Lower cap for test

    # Provide extreme signals in Provenance group
    raw_signals = {
        "shared_device": 1.0,
        "shared_ip": 1.0,
        "creation_burst": 1.0,
    }

    l_c, breakdown = calibrator.evaluate_cluster_evidence(raw_signals)
    prov = breakdown["Provenance"]

    # Sum of individual signals exceeds cap, but capped_evidence must not exceed e_max
    assert prov.raw_sum > 3.0
    assert prov.capped_evidence == 3.0


def test_gate_rule_invariant_9_2_1():
    # Case 1: Behavior only (Content + Behavioral active, Provenance = 0)
    calibrator = EvidenceCalibrator()
    _, breakdown = calibrator.evaluate_cluster_evidence({
        "interval_regularity": 0.98,
        "synchronized_bursts": 0.95,
        "semantic_similarity": 0.99,
        "lexical_near_duplicates": 0.95,
        "shared_device": 0.0,
        "creation_burst": 0.0,
    })

    gate = EvidenceGate.evaluate_gate(breakdown)
    # Must NOT pass the gate! Invariant 9.2(1)
    assert gate.gate_passed is False
    assert gate.is_behavior_only is True
    assert "Gate REFUSED (Behavior-Only)" in gate.gate_reason

    # Case 2: Multi-group WITH Provenance (Bot farm multi-signal activation)
    _, breakdown2 = calibrator.evaluate_cluster_evidence({
        "shared_device": 0.98,
        "creation_burst": 0.96,
        "synchronized_bursts": 0.98,
        "semantic_similarity": 0.98,
    })
    gate2 = EvidenceGate.evaluate_gate(breakdown2)
    assert gate2.gate_passed is True
    assert gate2.has_active_provenance is True
    assert gate2.active_groups_count >= 2


def test_common_cause_test_passes():
    passed, msg = CorrelationAnalyzer.evaluate_common_cause_synthetic()
    assert passed is True
    assert "Common-cause test PASSED" in msg
