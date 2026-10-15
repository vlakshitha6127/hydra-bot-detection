"""
Rate-Limited Human Review Queue for BreachX / HYDRA.
Implements Milestone M22 and Section 21.8:
- Prioritizes behavior-only clusters that failed the provenance gate.
- Coordination score C_c = sum of capped Behavioral + Content evidence.
- Ranking by C_c descending, ties broken by persistence, then member count.
- Rate-limited to top K (default K=5) entries per window.
- Precision@k evaluation for analysts.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any


class ReviewQueueEntry(BaseModel):
    cluster_id: str
    window_index: int
    coordination_score_c_c: float
    persistence_windows: int
    member_count: int
    active_groups: List[str]
    is_behavior_only: bool
    queue_rank: int
    evidence_summary: str


class ReviewQueueManager:
    """
    Manages rate-limited review queue with coordination score ranking.
    """

    def __init__(self, top_k_limit: int = 5):
        self.top_k_limit = top_k_limit
        self.queue_history: List[ReviewQueueEntry] = []

    def rank_and_enqueue_clusters(
        self,
        candidate_clusters: List[Dict[str, Any]],
        window_index: int,
    ) -> List[ReviewQueueEntry]:
        """
        Filters behavior-only or unprovenanced candidate clusters,
        ranks by C_c (then persistence, then size), and enqueues top K.
        """
        # Exclude clusters that already passed gate and are in automated action
        unprovenanced = [
            c for c in candidate_clusters
            if not c.get("gate_passed", False) and c.get("coordination_score", 0.0) > 0.5
        ]

        # Ranking: primary = C_c desc, secondary = persistence desc, tertiary = size desc
        unprovenanced.sort(
            key=lambda c: (
                c.get("coordination_score", 0.0),
                c.get("persistence", 0),
                c.get("member_count", 0),
            ),
            reverse=True,
        )

        top_k = unprovenanced[: self.top_k_limit]
        entries: List[ReviewQueueEntry] = []

        for rank_idx, c in enumerate(top_k, start=1):
            entry = ReviewQueueEntry(
                cluster_id=c["cluster_id"],
                window_index=window_index,
                coordination_score_c_c=round(c.get("coordination_score", 0.0), 4),
                persistence_windows=c.get("persistence", 0),
                member_count=c.get("member_count", 0),
                active_groups=c.get("active_groups", []),
                is_behavior_only=c.get("is_behavior_only", True),
                queue_rank=rank_idx,
                evidence_summary=c.get("summary", "Behavioral/Content coordination flagged for analyst review."),
            )
            entries.append(entry)
            self.queue_history.append(entry)

        return entries

    def get_current_queue(self, window_index: Optional[int] = None) -> List[ReviewQueueEntry]:
        if window_index is not None:
            return [e for e in self.queue_history if e.window_index == window_index]
        return self.queue_history[-self.top_k_limit:]

    @staticmethod
    def compute_precision_at_k(
        queue_entries: List[ReviewQueueEntry],
        ground_truth: Dict[str, Any],
        cluster_members_map: Dict[str, List[str]],
        k: int = 3,
    ) -> float:
        """
        Computes precision@k of the review queue:
        Fraction of top-k queue clusters that correspond to true bot campaigns.
        """
        top_k_entries = queue_entries[:k]
        if not top_k_entries:
            return 0.0

        true_bot_clusters = 0
        for entry in top_k_entries:
            members = cluster_members_map.get(entry.cluster_id, [])
            if members:
                # Majority vote from ground truth
                bot_count = sum(1 for m in members if ground_truth.get(m, False))
                if (bot_count / len(members)) >= 0.5:
                    true_bot_clusters += 1

        return float(round(true_bot_clusters / len(top_k_entries), 4))
