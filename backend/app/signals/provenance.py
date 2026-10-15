"""
Provenance Signal Extractor for BreachX / HYDRA.
Implements:
- Shared Device Fingerprint (rarity-weighted pairwise links)
- Shared IP Range (popularity down-weighted links)
- Creation Timing Burst (concentration of creation times vs baseline)
Follows Sections 5, 6.2, 21.1.
"""

import math
from typing import List, Dict, Set, Tuple, Optional
import numpy as np
from backend.app.schemas.event import Account


class ProvenanceSignals:
    """
    Computes infrastructure provenance signals across cluster accounts.
    """

    @staticmethod
    def compute_device_sharing(
        cluster_accounts: List[Account],
        global_accounts: Dict[str, Account],
    ) -> float:
        """
        Calculates device sharing density within the cluster normalized by total pairs.
        Returns a score in [0, 1].
        """
        if len(cluster_accounts) < 2:
            return 0.0

        device_global_freq: Dict[str, int] = {}
        for acc in global_accounts.values():
            if acc.device_hash:
                device_global_freq[acc.device_hash] = device_global_freq.get(acc.device_hash, 0) + 1

        total_pairs = (len(cluster_accounts) * (len(cluster_accounts) - 1)) // 2
        weighted_shared = 0.0

        for i in range(len(cluster_accounts)):
            for j in range(i + 1, len(cluster_accounts)):
                d1 = cluster_accounts[i].device_hash
                d2 = cluster_accounts[j].device_hash
                if d1 and d2 and d1 == d2:
                    n_glob = device_global_freq.get(d1, 2)
                    # Rare hardware sharing has high weight
                    rarity_weight = 1.0 / math.log2(1.0 + n_glob)
                    weighted_shared += rarity_weight

        if total_pairs == 0:
            return 0.0

        # Density of rarity-weighted shared pairs
        # For a botnet where accounts share a small set of devices, this is high
        shared_fraction = weighted_shared / total_pairs
        # Scale appropriately so that sharing among 4 devices out of 40 yields strong signal (>0.4)
        scaled = min(1.0, shared_fraction * 4.0)
        return float(scaled)

    @staticmethod
    def compute_ip_sharing(
        cluster_accounts: List[Account],
        global_accounts: Dict[str, Account],
    ) -> float:
        """
        Calculates IP range sharing with rarity weighting.
        Inverse popularity down-weights common subnets like campus NAT.
        Returns a score in [0, 1].
        """
        if len(cluster_accounts) < 2:
            return 0.0

        ip_global_freq: Dict[str, int] = {}
        for acc in global_accounts.values():
            if acc.ip_range_hash:
                ip_global_freq[acc.ip_range_hash] = ip_global_freq.get(acc.ip_range_hash, 0) + 1

        total_pairs = (len(cluster_accounts) * (len(cluster_accounts) - 1)) // 2
        weighted_shared = 0.0

        for i in range(len(cluster_accounts)):
            for j in range(i + 1, len(cluster_accounts)):
                ip1 = cluster_accounts[i].ip_range_hash
                ip2 = cluster_accounts[j].ip_range_hash
                if ip1 and ip2 and ip1 == ip2:
                    n_glob = ip_global_freq.get(ip1, 2)
                    # Popular IP subnets (n_glob >= 30) get heavily discounted
                    rarity_weight = 1.0 / math.log2(2.0 + n_glob)
                    weighted_shared += rarity_weight

        if total_pairs == 0:
            return 0.0

        # Average pair weight across cluster
        avg_weight = weighted_shared / total_pairs
        # For campus NAT (n_glob=30), avg_weight is 1/log2(32) = 0.20
        return float(min(1.0, avg_weight))

    @staticmethod
    def compute_creation_burst(
        cluster_accounts: List[Account],
        baseline_time_span: float = 30000000.0,
    ) -> float:
        """
        Measures temporal concentration of creation times within the cluster.
        Uses sliding window concentration / IQR to be robust to intentional noise injection (§20.3).
        Single accounts or small clusters (< 3) do not constitute a coordinated creation burst.
        """
        if len(cluster_accounts) < 3:
            return 0.0

        times = np.array(sorted([acc.created_at for acc in cluster_accounts]))

        # Measure the maximum fraction of cluster accounts created within a 1-hour (3600s) window
        max_in_hour = 1
        for i in range(len(times)):
            count = np.sum((times >= times[i]) & (times <= times[i] + 3600.0))
            if count > max_in_hour:
                max_in_hour = count

        concentration_ratio = max_in_hour / len(times)

        # Also measure interquartile span (p25 to p75)
        p25 = np.percentile(times, 25)
        p75 = np.percentile(times, 75)
        iqr_span = max(1.0, p75 - p25)

        # If 70%+ of the accounts were created within an hour, burst is near 1.0
        if concentration_ratio >= 0.70 or iqr_span <= 3600.0:
            return float(min(1.0, 0.7 + (0.3 * concentration_ratio)))

        # Otherwise evaluate based on span
        log_span = math.log10(max(60.0, iqr_span))
        max_log = math.log10(baseline_time_span)  # ~7.47
        min_log = math.log10(3600.0)  # ~3.55

        if log_span >= max_log:
            return 0.0

        score = 1.0 - ((log_span - min_log) / (max_log - min_log))
        return float(max(0.0, min(1.0, score)))
