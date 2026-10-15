import pytest
from backend.app.simulator.config import get_scenario_config
from backend.app.simulator.generator import EventSimulator
from backend.app.graph.builder import GraphBuilder
from backend.app.graph.clustering import CommunityDetector


@pytest.fixture(scope="module")
def s2_run():
    config = get_scenario_config("S2", seed=42)
    sim = EventSimulator(config)
    data = sim.generate_simulation()
    return sim, data


def test_campus_nat_does_not_form_false_cluster(s2_run):
    sim, data = s2_run
    builder = GraphBuilder()
    detector = CommunityDetector(seed=42)

    # Window 1 (before bot campaign launches)
    w1 = data.windows[1]
    G = builder.build_graph(sim.accounts, w1.posts, w1.interactions)
    clusters = detector.detect_communities(G)

    # Decoy C (Campus NAT) accounts should NOT form a dense cluster on IP alone
    nat_accounts = set(aid for aid, lbl in data.ground_truth.items() if lbl.actor_type.value == "decoy_nat")

    for cl in clusters:
        # Check intersection with campus NAT accounts
        nat_in_cluster = cl.intersection(nat_accounts)
        # Rarity weighting must prevent all 30 NAT accounts from clustering together
        assert len(nat_in_cluster) < 15, "Campus NAT formed a false cluster due to common IP!"


def test_bot_farm_forms_recognizable_cluster(s2_run):
    sim, data = s2_run
    builder = GraphBuilder()
    detector = CommunityDetector(seed=42)

    # Window 3 (active bot campaign)
    w3 = data.windows[3]
    G = builder.build_graph(sim.accounts, w3.posts, w3.interactions)
    clusters = detector.detect_communities(G)

    bot_accounts = set(aid for aid, lbl in data.ground_truth.items() if lbl.is_bot)

    # There must be a detected cluster containing the majority of bot farm accounts
    farm_cluster_found = False
    for cl in clusters:
        overlap = cl.intersection(bot_accounts)
        if len(overlap) >= 20:  # At least 20 of 40 bot accounts grouped
            farm_cluster_found = True
            break

    assert farm_cluster_found, "Bot farm was not detected as a recognizable cluster in window 3!"


def test_clustering_is_seeded_and_stable(s2_run):
    sim, data = s2_run
    builder = GraphBuilder()
    detector1 = CommunityDetector(seed=42)
    detector2 = CommunityDetector(seed=42)

    w3 = data.windows[3]
    G = builder.build_graph(sim.accounts, w3.posts, w3.interactions)

    c1 = detector1.detect_communities(G)
    c2 = detector2.detect_communities(G)

    assert c1 == c2, "Louvain clustering with identical seed produced non-deterministic output!"
