import pytest
import os
from backend.app.simulator.config import get_scenario_config
from backend.app.evaluation.suite import EvaluationSuite
from backend.app.evaluation.ablation import AblationRunner


def test_s1_zero_decoy_restrictions():
    """
    Release Gate Minimum Viable Result (§21.10):
    Scenario S1 (Clean baseline with Fan community, News accounts, and Campus NAT)
    MUST produce exactly ZERO user-impacting actions on decoys.
    """
    s1_cfg = get_scenario_config("S1", seed=42)
    suite = EvaluationSuite()
    result = suite.run_pipeline(s1_cfg)

    # Must have 0 decoy restrictions
    assert result.metrics["decoy_restricted_count"] == 0
    assert result.metrics["decoy_restriction_rate"] == 0.0
    assert result.metrics["background_fpr"] == 0.0


def test_s2_bot_farm_escalation():
    """
    Release Gate Minimum Viable Result (§21.10):
    In Scenario S2, the bot farm reaches Throttle within N windows (N <= 10).
    """
    s2_cfg = get_scenario_config("S2", seed=42)
    suite = EvaluationSuite()
    result = suite.run_pipeline(s2_cfg)

    assert result.metrics["farm_recall"] > 0.5
    assert result.metrics["detection_delay_throttle"] is not None
    assert result.metrics["detection_delay_throttle"] <= 10  # Spec Section 21.10: N = 10 windows
    assert result.metrics["decoy_restriction_rate"] == 0.0


def test_ablation_and_baselines_report_generation():
    """
    Computes ablation matrix and generates docs/EVALUATION_REPORT.md.
    """
    runner = AblationRunner()
    ablation_matrix = runner.run_ablation_matrix(seed=42)
    baselines = runner.run_baseline_comparison(seed=42)

    assert len(ablation_matrix) > 0
    assert len(baselines) == 3

    # Check no-provenance condition for S2
    no_prov_s2 = next(r for r in ablation_matrix if r["scenario_id"] == "S2" and r["condition_id"] == "no_provenance")
    # With Provenance disabled, farm recall of automated restrictions must be 0% (§21.10)
    assert no_prov_s2["bot_farm_recall_pct"] == 0.0

    report_md = runner.generate_markdown_report(ablation_matrix, baselines)
    assert "# BreachX 2026 / HYDRA: Comprehensive Evaluation Report" in report_md

    docs_dir = os.path.join(os.path.dirname(__file__), "..", "..", "docs")
    os.makedirs(docs_dir, exist_ok=True)
    report_path = os.path.join(docs_dir, "EVALUATION_REPORT.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    assert os.path.exists(report_path)
