"""
Tests for Rate-Limited Human Review Queue (Milestone M22, Section 21.8).
Verifies:
1. Candidate filtering: Behavior-only and unprovenanced clusters are enqueued.
2. Ranking: Ordered by coordination score C_c descending, ties broken by persistence then size.
3. Rate limiting: Capped strictly at top K (default K=5) per window.
4. Precision@k evaluation calculation.
"""

import pytest
from backend.app.policy.review_queue import ReviewQueueManager, ReviewQueueEntry


def test_review_queue_ranking_and_rate_limit():
    mgr = ReviewQueueManager(top_k_limit=5)

    candidate_clusters = [
        # Cluster 1: Passes gate -> should NOT be in unprovenanced review queue
        {
            "cluster_id": "c_auto_action",
            "gate_passed": True,
            "coordination_score": 6.5,
            "persistence": 4,
            "member_count": 30,
            "active_groups": ["Provenance", "Behavioral"],
            "is_behavior_only": False,
        },
        # Cluster 2: High coordination score, behavior-only
        {
            "cluster_id": "c_evasive_bot_1",
            "gate_passed": False,
            "coordination_score": 5.2,
            "persistence": 3,
            "member_count": 25,
            "active_groups": ["Behavioral", "Content"],
            "is_behavior_only": True,
        },
        # Cluster 3: Same coordination score as c_evasive_bot_1, but higher persistence
        {
            "cluster_id": "c_evasive_bot_persistent",
            "gate_passed": False,
            "coordination_score": 5.2,
            "persistence": 5,
            "member_count": 20,
            "active_groups": ["Behavioral", "Content"],
            "is_behavior_only": True,
        },
        # Cluster 4: Moderate coordination
        {
            "cluster_id": "c_fan_community_flock",
            "gate_passed": False,
            "coordination_score": 2.8,
            "persistence": 2,
            "member_count": 15,
            "active_groups": ["Content"],
            "is_behavior_only": True,
        },
        # Cluster 5: Low coordination
        {
            "cluster_id": "c_low_coord_1",
            "gate_passed": False,
            "coordination_score": 1.5,
            "persistence": 1,
            "member_count": 5,
            "active_groups": ["Behavioral"],
            "is_behavior_only": True,
        },
        # Cluster 6: Low coordination
        {
            "cluster_id": "c_low_coord_2",
            "gate_passed": False,
            "coordination_score": 1.2,
            "persistence": 1,
            "member_count": 4,
            "active_groups": ["Behavioral"],
            "is_behavior_only": True,
        },
        # Cluster 7: Low coordination, should exceed top K=5
        {
            "cluster_id": "c_overflow_cluster",
            "gate_passed": False,
            "coordination_score": 0.8,
            "persistence": 1,
            "member_count": 3,
            "active_groups": ["Content"],
            "is_behavior_only": True,
        },
    ]

    enqueued = mgr.rank_and_enqueue_clusters(candidate_clusters, window_index=1)

    # 1. Rate limit check: Maximum 5 entries
    assert len(enqueued) == 5

    # 2. Automated action cluster excluded
    enqueued_ids = [e.cluster_id for e in enqueued]
    assert "c_auto_action" not in enqueued_ids
    assert "c_overflow_cluster" not in enqueued_ids

    # 3. Tie-breaking check:
    # Both 'c_evasive_bot_persistent' and 'c_evasive_bot_1' have C_c = 5.2,
    # but 'c_evasive_bot_persistent' has persistence 5 vs 3, so it MUST be ranked #1!
    assert enqueued[0].cluster_id == "c_evasive_bot_persistent"
    assert enqueued[0].queue_rank == 1
    assert enqueued[1].cluster_id == "c_evasive_bot_1"
    assert enqueued[1].queue_rank == 2


def test_review_queue_precision_at_k():
    entries = [
        ReviewQueueEntry(
            cluster_id="c_true_bot_farm",
            window_index=1,
            coordination_score_c_c=4.5,
            persistence_windows=3,
            member_count=10,
            active_groups=["Behavioral", "Content"],
            is_behavior_only=True,
            queue_rank=1,
            evidence_summary="Synced bursts",
        ),
        ReviewQueueEntry(
            cluster_id="c_fan_flock",
            window_index=1,
            coordination_score_c_c=3.2,
            persistence_windows=2,
            member_count=8,
            active_groups=["Content"],
            is_behavior_only=True,
            queue_rank=2,
            evidence_summary="Hashtag storm",
        ),
        ReviewQueueEntry(
            cluster_id="c_evasive_farm_2",
            window_index=1,
            coordination_score_c_c=2.9,
            persistence_windows=2,
            member_count=6,
            active_groups=["Behavioral", "Content"],
            is_behavior_only=True,
            queue_rank=3,
            evidence_summary="Interval regularity",
        ),
    ]

    cluster_members = {
        "c_true_bot_farm": [f"bot_{i}" for i in range(10)],
        "c_fan_flock": [f"fan_{i}" for i in range(8)],
        "c_evasive_farm_2": [f"bot_evasive_{i}" for i in range(6)],
    }

    ground_truth = {}
    for i in range(10):
        ground_truth[f"bot_{i}"] = True
    for i in range(8):
        ground_truth[f"fan_{i}"] = False
    for i in range(6):
        ground_truth[f"bot_evasive_{i}"] = True

    # At k=1: 1/1 = 1.0
    p1 = ReviewQueueManager.compute_precision_at_k(entries, ground_truth, cluster_members, k=1)
    assert p1 == 1.0

    # At k=2: 1/2 = 0.5 (c_true_bot_farm is bot, c_fan_flock is not)
    p2 = ReviewQueueManager.compute_precision_at_k(entries, ground_truth, cluster_members, k=2)
    assert p2 == 0.5

    # At k=3: 2/3 = 0.6667
    p3 = ReviewQueueManager.compute_precision_at_k(entries, ground_truth, cluster_members, k=3)
    assert p3 == pytest.approx(0.6667, abs=1e-3)
