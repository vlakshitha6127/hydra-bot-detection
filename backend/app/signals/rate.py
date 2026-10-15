"""
Contextual Posting Rate Signal for BreachX / HYDRA.
Note (§5, §8, §21.1):
Posting rate is a contextual modifier, NOT independent evidence of coordination alone.
It exists so high-volume news accounts visibly trip a signal, but cannot satisfy the gate alone.
Never counted as an active evidence group towards automated restrictions.
"""

from typing import List, Set
from backend.app.schemas.event import Post


class RateSignals:
    """
    Computes per-account and cluster posting rate relative to population baseline.
    """

    @staticmethod
    def compute_posting_rate(
        posts: List[Post],
        cluster_member_ids: Set[str],
        baseline_rate_per_member: float = 2.0,  # Expected posts per window per member
    ) -> float:
        """
        Returns normalized rate multiplier in [0, 1].
        """
        if not cluster_member_ids:
            return 0.0

        cluster_posts = [p for p in posts if p.account_id in cluster_member_ids]
        actual_rate = len(cluster_posts) / len(cluster_member_ids)

        # High rate (e.g. 4+ posts per window) scores high
        ratio = actual_rate / max(0.5, baseline_rate_per_member)
        normalized = min(1.0, ratio / 3.0)
        return float(normalized)
