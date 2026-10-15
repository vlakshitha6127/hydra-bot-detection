import pytest
from backend.app.evaluation.claims import ClaimAuditor


def test_claim_auditor_flags_forbidden_claims():
    bad_pitch = "Our revolutionary system detects all bots with 100% accuracy and works on real platforms!"
    is_valid, violations, _ = ClaimAuditor.audit_text(bad_pitch)

    assert is_valid is False
    assert len(violations) >= 2
    assert any("detects all bots" in v for v in violations)
    assert any("100% accuracy" in v for v in violations)


def test_claim_auditor_passes_compliant_claims():
    good_pitch = (
        "On our simulated synthetic-data result benchmark, the hybrid system separated the "
        "simulated bot-farm cluster from decoy communities, with signal-level explanations and no "
        "automated permanent action from any single weak signal."
    )
    is_valid, violations, disclaimers = ClaimAuditor.audit_text(good_pitch)

    assert is_valid is True
    assert len(violations) == 0
    assert "synthetic-data result" in disclaimers
