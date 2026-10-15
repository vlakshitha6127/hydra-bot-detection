import pytest
from backend.app.simulator.config import get_scenario_config
from backend.app.simulator.generator import EventSimulator
from backend.app.signals.extractor import SignalExtractor


@pytest.fixture(scope="module")
def s2_sim_data():
    config = get_scenario_config("S2", seed=42)
    sim = EventSimulator(config)
    return sim, sim.generate_simulation()


def test_signals_separation_on_bot_farm(s2_sim_data):
    sim, data = s2_sim_data
    extractor = SignalExtractor()

    # Get accounts by group
    bot_members = set(aid for aid, lbl in data.ground_truth.items() if lbl.is_bot)
    bg_members = set(aid for aid, lbl in data.ground_truth.items() if lbl.actor_type.value == "background")

    # In window 3 (when bot campaign is active)
    w3 = data.windows[3]
    bot_signals = extractor.extract_cluster_signals(bot_members, sim.accounts, w3.posts, w3.interactions)
    bg_signals = extractor.extract_cluster_signals(set(list(bg_members)[:40]), sim.accounts, w3.posts, w3.interactions)

    # 1. Provenance: Bot farm must have significant shared device and creation burst compared to background
    assert bot_signals["shared_device"] > bg_signals["shared_device"]
    assert bot_signals["creation_burst"] > 0.8
    assert bg_signals["creation_burst"] < 0.2

    # 2. Timing: Bot farm has high synchrony
    assert bot_signals["synchronized_bursts"] > bg_signals["synchronized_bursts"]

    # 3. Content: Bot farm has significant lexical near-duplicates and semantic similarity
    assert bot_signals["lexical_near_duplicates"] > 0.05
    assert bot_signals["semantic_similarity"] > bg_signals["semantic_similarity"]


def test_decoy_a_fan_trips_content_only(s2_sim_data):
    sim, data = s2_sim_data
    extractor = SignalExtractor()
    fan_members = set(aid for aid, lbl in data.ground_truth.items() if lbl.actor_type.value == "decoy_fan")

    w2 = data.windows[2]
    fan_signals = extractor.extract_cluster_signals(fan_members, sim.accounts, w2.posts, w2.interactions)

    # Decoy A trips Content (semantic similarity)
    assert fan_signals["semantic_similarity"] > 0.2

    # Decoy A does NOT trip Provenance (no shared hardware, organic creation times)
    assert fan_signals["shared_device"] == 0.0
    assert fan_signals["creation_burst"] < 0.2


def test_decoy_b_news_trips_rate_and_regularity_only(s2_sim_data):
    sim, data = s2_sim_data
    extractor = SignalExtractor()
    news_members = set(aid for aid, lbl in data.ground_truth.items() if lbl.actor_type.value == "decoy_news")

    w2 = data.windows[2]
    news_signals = extractor.extract_cluster_signals(news_members, sim.accounts, w2.posts, w2.interactions)

    # Decoy B trips regularity and posting rate
    assert news_signals["interval_regularity"] > 0.8
    assert news_signals["posting_rate"] > 0.5

    # Decoy B does NOT trip multi-account content spam or burst signup
    assert news_signals["creation_burst"] < 0.2
    assert news_signals["shared_device"] == 0.0


def test_decoy_c_campus_nat_ip_rarity_downweighting(s2_sim_data):
    sim, data = s2_sim_data
    extractor = SignalExtractor()
    nat_members = set(aid for aid, lbl in data.ground_truth.items() if lbl.actor_type.value == "decoy_nat")

    w2 = data.windows[2]
    nat_signals = extractor.extract_cluster_signals(nat_members, sim.accounts, w2.posts, w2.interactions)

    # Because IP is shared by 30 accounts, rarity weighting prevents it from maxing out
    assert nat_signals["shared_ip"] < 0.4
    # Hardware device sharing is zero
    assert nat_signals["shared_device"] == 0.0
