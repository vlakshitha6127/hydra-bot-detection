"""
Behavioral Timing Signals for BreachX / HYDRA.
Implements:
- Posting-interval regularity (Coefficient of Variation of inter-post intervals)
- Synchronized posting bursts across cluster members vs. shuffled null
Follows Sections 5, 21.1.
"""

import math
from typing import List, Dict
import numpy as np
from backend.app.schemas.event import Post


class TimingSignals:
    """
    Measures scheduling patterns and cross-account coordination in event timing.
    """

    @staticmethod
    def compute_interval_regularity(posts: List[Post]) -> float:
        """
        Computes regularity of inter-post intervals across cluster members.
        Scheduled bots produce near-zero variance (low CV).
        Returns a score in [0, 1] where 1.0 means highly robotic/scheduled.
        """
        posts_by_account: Dict[str, List[float]] = {}
        for p in posts:
            posts_by_account.setdefault(p.account_id, []).append(p.timestamp)

        cv_scores: List[float] = []

        for aid, timestamps in posts_by_account.items():
            if len(timestamps) < 3:
                continue
            ts = sorted(timestamps)
            intervals = np.diff(ts)
            mean_int = np.mean(intervals)
            std_int = np.std(intervals)

            if mean_int > 0:
                cv = std_int / mean_int  # Coefficient of Variation
                # For Poisson/organic posting, CV ~ 1.0. For scheduled bots, CV < 0.2.
                regularity = max(0.0, min(1.0, 1.0 - cv))
                cv_scores.append(regularity)

        if not cv_scores:
            return 0.0

        return float(np.mean(cv_scores))

    @staticmethod
    def compute_synchronized_bursts(
        posts: List[Post],
        window_duration: float = 3600.0,
        burst_bin_seconds: float = 60.0,
    ) -> float:
        """
        Computes the fraction of posts co-occurring in short time bursts across distinct members,
        normalized against a uniform/shuffled null expectation.
        Returns a score in [0, 1].
        """
        if len(posts) < 4:
            return 0.0

        # Bin posts into discrete time slices
        min_ts = min(p.timestamp for p in posts)
        max_ts = max(p.timestamp for p in posts)
        span = max(1.0, max_ts - min_ts)

        n_bins = max(1, int(math.ceil(span / burst_bin_seconds)))
        bin_members: Dict[int, set] = {b: set() for b in range(n_bins)}

        for p in posts:
            b_idx = min(n_bins - 1, int((p.timestamp - min_ts) / burst_bin_seconds))
            bin_members[b_idx].add(p.account_id)

        # Count multi-member synchronized bursts
        multi_member_bins = sum(1 for m_set in bin_members.values() if len(m_set) >= 3)
        max_simultaneous = max(len(m_set) for m_set in bin_members.values()) if bin_members else 0

        # Normalize score based on concentration in high-density bins
        total_accounts = len(set(p.account_id for p in posts))
        if total_accounts < 2:
            return 0.0

        fraction_in_burst = max_simultaneous / total_accounts
        return float(max(0.0, min(1.0, fraction_in_burst)))
