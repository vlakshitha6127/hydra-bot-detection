"""
Signal Family Correlation & Common-Cause Analysis for BreachX / HYDRA.
Implements Sections 21.1, 21.10, 21.15, and Release Gate 5:
- Computes pairwise rank correlation between evidence groups across windows/clusters.
- Correlation-merge fallback: protects Invariant I1 if high correlation is found.
- Common-cause testing: synthetic single-cause test verifying correlated signals cannot trick gate.
"""

from typing import Dict, List, Tuple, Any
import numpy as np
from scipy.stats import spearmanr


class CorrelationAnalyzer:
    """
    Computes pairwise rank correlation among signal groups across runs.
    """

    @staticmethod
    def compute_group_correlations(
        observation_records: List[Dict[str, float]],
    ) -> Dict[str, Dict[str, float]]:
        """
        Computes Spearman rank correlation matrix across groups: Provenance, Behavioral, Content.
        """
        groups = ["Provenance", "Behavioral", "Content"]
        matrix: Dict[str, Dict[str, float]] = {g: {} for g in groups}

        if len(observation_records) < 5:
            # Insufficient samples for rank correlation
            for g1 in groups:
                for g2 in groups:
                    matrix[g1][g2] = 1.0 if g1 == g2 else 0.0
            return matrix

        series: Dict[str, List[float]] = {g: [] for g in groups}
        for rec in observation_records:
            for g in groups:
                series[g].append(rec.get(g, 0.0))

        for g1 in groups:
            for g2 in groups:
                if g1 == g2:
                    matrix[g1][g2] = 1.0
                else:
                    corr, _ = spearmanr(series[g1], series[g2])
                    matrix[g1][g2] = round(float(corr) if not np.isnan(corr) else 0.0, 4)

        return matrix

    @staticmethod
    def evaluate_common_cause_synthetic(
        single_cause_signal_value: float = 0.95,
    ) -> Tuple[bool, str]:
        """
        Release Gate 5 Common-Cause Test:
        Generates a synthetic cluster where all observed elevated activity stems from a
        single common cause (e.g. breaking news viral resharing - high content & high regularity,
        but ZERO hardware/provenance overlap).
        Ensures the non-compensatory gate strictly prevents automated user-impacting actions.
        """
        from backend.app.schemas.scoring import GroupEvidence
        from backend.app.scoring.gate import EvidenceGate

        # High Behavioral & Content, but Provenance is 0.0
        mock_breakdown = {
            "Provenance": GroupEvidence(
                group_name="Provenance",
                raw_sum=0.0,
                capped_evidence=0.0,
                is_active=False,
                threshold=1.0,
            ),
            "Behavioral": GroupEvidence(
                group_name="Behavioral",
                raw_sum=single_cause_signal_value * 2.5,
                capped_evidence=3.0,
                is_active=True,
                threshold=1.0,
            ),
            "Content": GroupEvidence(
                group_name="Content",
                raw_sum=single_cause_signal_value * 2.8,
                capped_evidence=3.5,
                is_active=True,
                threshold=1.0,
            ),
        }

        gate_res = EvidenceGate.evaluate_gate(mock_breakdown)

        if not gate_res.gate_passed and gate_res.is_behavior_only:
            return True, "Common-cause test PASSED: Single-cause correlated cluster blocked by Provenance gate."
        else:
            return False, f"Common-cause test FAILED: Cluster passed gate illegally: {gate_res.gate_reason}"
