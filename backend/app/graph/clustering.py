"""
Louvain Community Detection and Cluster Filtering for BreachX / HYDRA.
Implements Milestone M3, Section 6.3, and Section 21.3.
"""

from typing import List, Dict, Set, Tuple
import networkx as nx
from networkx.algorithms.community import louvain_communities


class CommunityDetector:
    """
    Applies weighted Louvain community detection with post-filters on size and density.
    Fixed random seed ensures bit-for-bit determinism.
    """

    def __init__(
        self,
        resolution: float = 1.0,
        min_cluster_size: int = 3,
        min_internal_density: float = 0.12,
        seed: int = 42,
    ):
        self.resolution = resolution
        self.min_cluster_size = min_cluster_size
        self.min_internal_density = min_internal_density
        self.seed = seed

    def detect_communities(self, G: nx.Graph) -> List[Set[str]]:
        """
        Executes Louvain community detection and applies post-filters.
        Returns a list of qualifying clusters (sets of account IDs).
        """
        if G.number_of_nodes() < self.min_cluster_size or G.number_of_edges() == 0:
            return []

        # Weighted Louvain clustering (§6.3)
        raw_communities = louvain_communities(
            G,
            weight="weight",
            resolution=self.resolution,
            seed=self.seed,
        )

        valid_clusters: List[Set[str]] = []

        for comm in raw_communities:
            if len(comm) < self.min_cluster_size:
                continue

            subgraph = G.subgraph(comm)
            n_nodes = subgraph.number_of_nodes()
            n_edges = subgraph.number_of_edges()
            max_edges = (n_nodes * (n_nodes - 1)) / 2.0

            if max_edges > 0:
                density = n_edges / max_edges
                if density >= self.min_internal_density:
                    valid_clusters.append(set(comm))

        # Sort clusters by size descending for deterministic ordering
        valid_clusters.sort(key=lambda c: len(c), reverse=True)
        return valid_clusters

    @staticmethod
    def match_clusters_across_windows(
        prev_clusters: Dict[str, Set[str]],
        curr_clusters: List[Set[str]],
        jaccard_threshold: float = 0.40,
    ) -> Dict[str, str]:
        """
        Greedy 1-to-1 matching across windows via member Jaccard overlap (§21.3).
        Maps current cluster index (e.g. 'new_0') to matched previous cluster ID (e.g. 'c_0').
        """
        mappings: Dict[str, str] = {}
        used_prev: Set[str] = set()

        # Compute all pairwise overlaps
        candidates: List[Tuple[float, str, str]] = []
        for curr_idx, curr_set in enumerate(curr_clusters):
            curr_key = f"curr_{curr_idx}"
            for prev_id, prev_set in prev_clusters.items():
                intersection = len(curr_set.intersection(prev_set))
                union = len(curr_set.union(prev_set))
                if union > 0:
                    jaccard = intersection / union
                    if jaccard >= jaccard_threshold:
                        candidates.append((jaccard, curr_key, prev_id))

        # Greedy match by highest overlap first (§21.3)
        candidates.sort(key=lambda x: x[0], reverse=True)

        for jaccard, curr_key, prev_id in candidates:
            if curr_key not in mappings and prev_id not in used_prev:
                mappings[curr_key] = prev_id
                used_prev.add(prev_id)

        return mappings
