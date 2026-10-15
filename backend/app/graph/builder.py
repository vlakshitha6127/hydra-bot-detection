"""
Account Graph Construction with Rarity Weighting for BreachX / HYDRA.
Implements Milestone M3 and Section 6.
"""

import math
from typing import List, Dict, Set, Tuple, Optional
import networkx as nx
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.app.schemas.event import Account, Post, Interaction
from backend.app.schemas.graph import GraphNode, GraphEdge


class GraphBuilder:
    """
    Constructs weighted NetworkX graph of accounts with multi-modal edges.
    Applies inverse popularity rarity weighting (§6.2).
    """

    def __init__(
        self,
        weight_device: float = 1.0,
        weight_ip: float = 0.3,
        weight_content: float = 0.6,
        weight_timing: float = 0.5,
        weight_interaction: float = 0.7,
    ):
        self.w_device = weight_device
        self.w_ip = weight_ip
        self.w_content = weight_content
        self.w_timing = weight_timing
        self.w_interaction = weight_interaction
        self.hasher = HashingVectorizer(n_features=2**12, ngram_range=(1, 2), norm="l2")

    def build_graph(
        self,
        accounts: Dict[str, Account],
        posts: List[Post],
        interactions: List[Interaction],
    ) -> nx.Graph:
        """
        Builds a NetworkX weighted undirected graph.
        """
        G = nx.Graph()

        # Add all accounts as nodes
        for aid, acc in accounts.items():
            G.add_node(
                aid,
                device_hash=acc.device_hash,
                ip_range_hash=acc.ip_range_hash,
                created_at=acc.created_at,
            )

        edge_accumulator: Dict[Tuple[str, str], Dict[str, float]] = {}

        def add_edge_component(u: str, v: str, edge_type: str, weight: float):
            if u == v or weight <= 0.0:
                return
            pair = (min(u, v), max(u, v))
            if pair not in edge_accumulator:
                edge_accumulator[pair] = {}
            # Keep max weight for this specific edge type
            edge_accumulator[pair][edge_type] = max(
                edge_accumulator[pair].get(edge_type, 0.0), weight
            )

        # 1. Attribute Sharing: Shared Device (Rarity Weighted)
        device_users: Dict[str, List[str]] = {}
        for aid, acc in accounts.items():
            if acc.device_hash:
                device_users.setdefault(acc.device_hash, []).append(aid)

        for dev_hash, user_list in device_users.items():
            n_sharing = len(user_list)
            if n_sharing > 1:
                # Strong rarity weight for hardware sharing
                rarity_w = self.w_device / math.log2(1.0 + n_sharing)
                for i in range(n_sharing):
                    for j in range(i + 1, n_sharing):
                        add_edge_component(user_list[i], user_list[j], "device", rarity_w)

        # 2. Attribute Sharing: Shared IP Range (Popularity Down-Weighted)
        ip_users: Dict[str, List[str]] = {}
        for aid, acc in accounts.items():
            if acc.ip_range_hash:
                ip_users.setdefault(acc.ip_range_hash, []).append(aid)

        for ip_hash, user_list in ip_users.items():
            n_sharing = len(user_list)
            if n_sharing > 1:
                # Heavy down-weighting for popular IP subnets like campus NAT (§6.2)
                # If 30 accounts share an IP, log2(2 + 30) = 5.0 -> weight = 0.3 / 5.0 = 0.06
                rarity_w = self.w_ip / math.log2(2.0 + n_sharing)
                for i in range(n_sharing):
                    for j in range(i + 1, n_sharing):
                        add_edge_component(user_list[i], user_list[j], "ip", rarity_w)

        # 3. Content Similarity Edges
        # Only compare posts that exist in this window
        valid_posts = [p for p in posts if p.text.strip() and p.account_id in accounts]
        if len(valid_posts) > 1:
            try:
                feats = self.hasher.transform([p.text for p in valid_posts])
                sims = cosine_similarity(feats)
                for i in range(len(valid_posts)):
                    for j in range(i + 1, len(valid_posts)):
                        p1, p2 = valid_posts[i], valid_posts[j]
                        if p1.account_id != p2.account_id:
                            s = float(sims[i, j])
                            if s >= 0.35:
                                add_edge_component(
                                    p1.account_id,
                                    p2.account_id,
                                    "content",
                                    self.w_content * s,
                                )
            except Exception:
                pass

        # 4. Synchronized Timing Edges (posts within 60s)
        sorted_posts = sorted(valid_posts, key=lambda p: p.timestamp)
        for i in range(len(sorted_posts)):
            p1 = sorted_posts[i]
            for j in range(i + 1, len(sorted_posts)):
                p2 = sorted_posts[j]
                delta = p2.timestamp - p1.timestamp
                if delta > 60.0:
                    break
                if p1.account_id != p2.account_id:
                    timing_w = self.w_timing * max(0.0, 1.0 - (delta / 60.0))
                    add_edge_component(p1.account_id, p2.account_id, "timing", timing_w)

        # 5. Direct Interactions
        for inter in interactions:
            if inter.source_id in accounts and inter.target_id in accounts:
                add_edge_component(
                    inter.source_id, inter.target_id, "interaction", self.w_interaction
                )

        # Add aggregated edges to graph
        for (u, v), type_weights in edge_accumulator.items():
            combined_weight = sum(type_weights.values())
            # Normalize to avoid extreme outliers
            norm_weight = min(1.0, combined_weight)
            if norm_weight >= 0.08:  # Prune negligible edges
                G.add_edge(
                    u,
                    v,
                    weight=norm_weight,
                    edge_types=list(type_weights.keys()),
                )

        return G
