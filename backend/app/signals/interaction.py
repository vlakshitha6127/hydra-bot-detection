"""
Interaction Coordination Signals for BreachX / HYDRA.
Implements:
- Rapid reciprocal retweet/reply/like latency within candidate cluster
- Closed-loop amplification density
Follows Sections 5, 21.1.
"""

from typing import List, Set, Dict, Tuple
from backend.app.schemas.event import Interaction


class InteractionSignals:
    """
    Measures amplification and mutual interaction loops.
    """

    @staticmethod
    def compute_interaction_density(
        interactions: List[Interaction],
        cluster_member_ids: Set[str],
        rapid_latency_seconds: float = 30.0,
    ) -> float:
        """
        Measures intra-cluster reciprocal interaction speed and density.
        Returns a score in [0, 1].
        """
        if len(cluster_member_ids) < 2 or not interactions:
            return 0.0

        # Filter for interactions entirely within the cluster
        intra_interactions = [
            i for i in interactions
            if i.source_id in cluster_member_ids and i.target_id in cluster_member_ids
        ]

        if not intra_interactions:
            return 0.0

        # Check reciprocal pairs
        directed_edges: Set[Tuple[str, str]] = set()
        reciprocal_pairs = 0
        for i in intra_interactions:
            directed_edges.add((i.source_id, i.target_id))
            if (i.target_id, i.source_id) in directed_edges:
                reciprocal_pairs += 1

        n_members = len(cluster_member_ids)
        max_possible_edges = n_members * (n_members - 1)
        density = len(directed_edges) / max(1, max_possible_edges)

        # Scale density and reciprocal bonus
        score = min(1.0, (density * 2.0) + (reciprocal_pairs / max(1, n_members)))
        return float(score)
