import pytest
import os
from backend.app.simulator.config import get_scenario_config
from backend.app.simulator.generator import EventSimulator
from backend.app.simulator.validator import SimulatorValidator
from backend.app.schemas.event import ActorType


def test_simulator_determinism():
    config = get_scenario_config("S2", seed=42)
    sim1 = EventSimulator(config)
    data1 = sim1.generate_simulation()

    sim2 = EventSimulator(config)
    data2 = sim2.generate_simulation()

    assert len(data1.windows) == len(data2.windows)
    for w1, w2 in zip(data1.windows, data2.windows):
        assert len(w1.posts) == len(w2.posts)
        assert len(w1.interactions) == len(w2.interactions)
        for p1, p2 in zip(w1.posts, w2.posts):
            assert p1.post_id == p2.post_id
            assert p1.account_id == p2.account_id
            assert p1.timestamp == p2.timestamp
            assert p1.text == p2.text


def test_populations_composition():
    config = get_scenario_config("S2", seed=42)
    sim = EventSimulator(config)
    data = sim.generate_simulation()

    gt = data.ground_truth
    assert len(gt) > 150

    bots = [aid for aid, lbl in gt.items() if lbl.actor_type == ActorType.BOT]
    fans = [aid for aid, lbl in gt.items() if lbl.actor_type == ActorType.DECOY_FAN]
    news = [aid for aid, lbl in gt.items() if lbl.actor_type == ActorType.DECOY_NEWS]
    nat = [aid for aid, lbl in gt.items() if lbl.actor_type == ActorType.DECOY_NAT]

    assert len(bots) == 40
    assert len(fans) == 25
    assert len(news) == 2
    assert len(nat) == 30


def test_s1_baseline_has_zero_bots():
    config = get_scenario_config("S1", seed=42)
    sim = EventSimulator(config)
    data = sim.generate_simulation()

    bots = [aid for aid, lbl in data.ground_truth.items() if lbl.is_bot]
    assert len(bots) == 0


def test_validator_and_report_generation():
    config = get_scenario_config("S2", seed=42)
    validator = SimulatorValidator(config)
    report_data = validator.run_validation()

    assert report_data["is_deterministic"] is True
    assert report_data["release_gate_1_passed"] is True

    md_report = validator.generate_markdown_report(report_data)
    assert "# BreachX 2026 / HYDRA: Simulator Validation Report" in md_report
    assert "Release Gate 1 (Validation Report + Determinism): **VERIFIED & PASSED**" in md_report

    # Save to docs/SIMULATOR_VALIDATION.md as required by §20.3
    docs_dir = os.path.join(os.path.dirname(__file__), "..", "..", "docs")
    os.makedirs(docs_dir, exist_ok=True)
    report_path = os.path.join(docs_dir, "SIMULATOR_VALIDATION.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md_report)

    assert os.path.exists(report_path)
