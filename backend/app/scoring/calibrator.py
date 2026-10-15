"""
Evidence Scoring and Calibration Engine for BreachX / HYDRA.
Implements Sections 7.1, 21.2, 21.9, and Invariant I4:
- Null distribution percentile normalization against background groups.
- Monotone calibration map: f_s(x) = max(0, (x - x0_s) / (1 - x0_s)) with x0_s = 0.90.
- Signal evidence e_s = w_s * f_s(x_s).
- Group evidence E_g capped at E_max = 5.0.
- Additive cluster log-odds L_c = prior + sum over groups of capped E_g.
"""

from typing import Dict, List, Any, Tuple
import numpy as np

from backend.app.schemas.scoring import SignalEvidence, GroupEvidence

# Family to Group mapping (§21.1)
SIGNAL_METADATA = {
    "shared_device": {"family": "Identity", "group": "Provenance", "weight": 1.5, "x0": 0.05},
    "shared_ip": {"family": "Identity", "group": "Provenance", "weight": 1.0, "x0": 0.15},
    "creation_burst": {"family": "Creation timing", "group": "Provenance", "weight": 1.4, "x0": 0.30},
    "interval_regularity": {"family": "Behavioral timing", "group": "Behavioral", "weight": 1.2, "x0": 0.35},
    "synchronized_bursts": {"family": "Behavioral timing", "group": "Behavioral", "weight": 1.4, "x0": 0.15},
    "interaction_density": {"family": "Interaction", "group": "Behavioral", "weight": 1.0, "x0": 0.03},
    "semantic_similarity": {"family": "Content", "group": "Content", "weight": 1.5, "x0": 0.10},
    "lexical_near_duplicates": {"family": "Content", "group": "Content", "weight": 1.3, "x0": 0.05},
    "posting_rate": {"family": "Rate", "group": "Context", "weight": 0.8, "x0": 0.25},
}

GROUP_THRESHOLDS = {
    "Provenance": 0.8,
    "Behavioral": 0.6,
    "Content": 0.6,
    "Context": 999.0,  # Context never becomes an active evidence group
}

E_MAX = 5.0  # Max group evidence cap (§21.9)


class EvidenceCalibrator:
    """
    Calibrates raw cluster signals into additive log-odds evidence scores.
    """

    def __init__(self, e_max: float = E_MAX, group_thresholds: Dict[str, float] = None):
        self.e_max = e_max
        self.group_thresholds = group_thresholds or GROUP_THRESHOLDS

    @staticmethod
    def compute_null_percentile(raw_value: float, null_distribution: List[float]) -> float:
        """
        Computes percentile in [0, 1] of raw signal against background null.
        """
        if not null_distribution:
            # Fallback linear clipping if null is empty
            return float(max(0.0, min(1.0, raw_value)))
        arr = np.array(null_distribution)
        percentile = float(np.sum(arr <= raw_value) / len(arr))
        return percentile

    def calibrate_signal(
        self,
        signal_name: str,
        raw_val: float,
        null_dist: List[float] = None,
    ) -> SignalEvidence:
        """
        Calibrates a single signal into log-odds evidence.
        f_s(x) = max(0, (x - x0_s) / (1 - x0_s))
        e_s = w_s * f_s(x)
        """
        meta = SIGNAL_METADATA.get(
            signal_name,
            {"family": "Unknown", "group": "Context", "weight": 1.0, "x0": 0.90},
        )

        null_p = self.compute_null_percentile(raw_val, null_dist) if null_dist else raw_val
        x0 = meta["x0"]

        # Piecewise linear monotone map
        if null_p <= x0:
            calibrated = 0.0
        else:
            calibrated = (null_p - x0) / max(1e-5, (1.0 - x0))

        calibrated = min(1.0, calibrated)
        log_odds_e = meta["weight"] * calibrated

        return SignalEvidence(
            signal_name=signal_name,
            family=meta["family"],
            group=meta["group"],
            raw_value=round(raw_val, 4),
            null_percentile=round(null_p, 4),
            calibrated_value=round(calibrated, 4),
            weight=meta["weight"],
            log_odds_contribution=round(log_odds_e, 4),
        )

    def evaluate_cluster_evidence(
        self,
        raw_signals: Dict[str, float],
        null_distributions: Dict[str, List[float]] = None,
    ) -> Tuple[float, Dict[str, GroupEvidence]]:
        """
        Computes group evidence sums, applies E_max caps, and computes additive cluster L_c.
        Returns:
            (L_c, group_breakdown_dict)
        """
        null_distributions = null_distributions or {}
        signals_by_group: Dict[str, List[SignalEvidence]] = {
            "Provenance": [],
            "Behavioral": [],
            "Content": [],
            "Context": [],
        }

        for sig_name, raw_val in raw_signals.items():
            dist = null_distributions.get(sig_name, [])
            ev = self.calibrate_signal(sig_name, raw_val, dist)
            if ev.group in signals_by_group:
                signals_by_group[ev.group].append(ev)

        group_breakdown: Dict[str, GroupEvidence] = {}
        total_cluster_log_odds = 0.0

        for grp_name, sig_list in signals_by_group.items():
            raw_sum = sum(s.log_odds_contribution for s in sig_list)
            capped = min(self.e_max, raw_sum)
            threshold = self.group_thresholds.get(grp_name, 1.0)
            is_act = capped >= threshold and grp_name != "Context"

            group_breakdown[grp_name] = GroupEvidence(
                group_name=grp_name,
                raw_sum=round(raw_sum, 4),
                capped_evidence=round(capped, 4),
                is_active=is_act,
                threshold=threshold,
                signals=sig_list,
            )

            # L_c sums capped group values (excluding context modifier)
            if grp_name != "Context":
                total_cluster_log_odds += capped

        return round(total_cluster_log_odds, 4), group_breakdown
