"""
Content Coordination Signals for BreachX / HYDRA.
Implements:
- Semantic similarity (cosine similarity of text embeddings via deterministic hashing vectorizer)
- Lexical near-duplicate detection (MinHash / Jaccard on k-shingles)
Follows Sections 5, 21.1.
"""

from typing import List, Dict, Tuple
import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datasketch import MinHash

from backend.app.schemas.event import Post


class ContentSignals:
    """
    Computes semantic and lexical duplication across posts in a candidate cluster.
    """

    def __init__(self):
        # Deterministic fixed-dimensional feature hasher (no local corpus overfitting)
        self.hasher = HashingVectorizer(
            n_features=2**14,
            ngram_range=(1, 2),
            analyzer="word",
            norm="l2",
            alternate_sign=False,
        )

    def compute_semantic_similarity(
        self, posts: List[Post], similarity_threshold: float = 0.12
    ) -> float:
        """
        Computes pairwise semantic cosine similarity among cluster posts from distinct accounts.
        Returns the fraction of cross-account post pairs exceeding the similarity threshold.
        """
        if len(posts) < 2:
            return 0.0

        all_texts = [p.text for p in posts if p.text.strip()]
        if len(all_texts) < 2:
            return 0.0

        try:
            feat_matrix = self.hasher.transform(all_texts)
            sim_matrix = cosine_similarity(feat_matrix)
        except Exception:
            return 0.0

        cross_pairs = 0
        high_sim_pairs = 0

        for i in range(len(posts)):
            for j in range(i + 1, len(posts)):
                if posts[i].account_id != posts[j].account_id:
                    cross_pairs += 1
                    if sim_matrix[i, j] >= similarity_threshold:
                        high_sim_pairs += 1

        if cross_pairs == 0:
            return 0.0

        return float(min(1.0, high_sim_pairs / cross_pairs))

    @staticmethod
    def compute_lexical_near_duplicates(
        posts: List[Post],
        jaccard_threshold: float = 0.35,
        shingle_k: int = 2,
    ) -> float:
        """
        Uses MinHash with 2-shingles to detect exact and near-duplicate text coordination.
        Returns the fraction of cross-account pairs that share lexical Jaccard similarity.
        """
        if len(posts) < 2:
            return 0.0

        minhashes: List[Tuple[str, MinHash]] = []
        for p in posts:
            words = p.text.lower().split()
            m = MinHash(num_perm=64, seed=42)
            if len(words) >= shingle_k:
                for k_idx in range(len(words) - shingle_k + 1):
                    shingle = " ".join(words[k_idx : k_idx + shingle_k])
                    m.update(shingle.encode("utf-8"))
            else:
                for w in words:
                    m.update(w.encode("utf-8"))
            minhashes.append((p.account_id, m))

        cross_pairs = 0
        near_dup_pairs = 0

        for i in range(len(minhashes)):
            for j in range(i + 1, len(minhashes)):
                aid1, m1 = minhashes[i]
                aid2, m2 = minhashes[j]
                if aid1 != aid2:
                    cross_pairs += 1
                    sim = m1.jaccard(m2)
                    if sim >= jaccard_threshold:
                        near_dup_pairs += 1

        if cross_pairs == 0:
            return 0.0

        return float(min(1.0, near_dup_pairs / cross_pairs))
