"""
Signal Extractor Coordinator for BreachX / HYDRA.
Orchestrates signal computation across all 3 evidence groups + context modifier (§21.1).
"""

from typing import List, Dict, Set, Any
from backend.app.schemas.event import Account, Post, Interaction
from backend.app.signals.provenance import ProvenanceSignals
from backend.app.signals.timing import TimingSignals
from backend.app.signals.content import ContentSignals
from backend.app.signals.interaction import InteractionSignals
from backend.app.signals.rate import RateSignals


class SignalExtractor:
    """
    Computes all signals for a candidate cluster.
    """

    def __init__(self):
        self.content_engine = ContentSignals()

    def extract_cluster_signals(
        self,
        cluster_member_ids: Set[str],
        all_accounts: Dict[str, Account],
        window_posts: List[Post],
        window_interactions: List[Interaction],
    ) -> Dict[str, float]:
        """
        Extracts raw signal values in [0, 1] for all signal families.
        """
        cluster_accounts = [all_accounts[aid] for aid in cluster_member_ids if aid in all_accounts]
        cluster_posts = [p for p in window_posts if p.account_id in cluster_member_ids]

        # 1. Provenance Group
        sig_shared_device = ProvenanceSignals.compute_device_sharing(cluster_accounts, all_accounts)
        sig_shared_ip = ProvenanceSignals.compute_ip_sharing(cluster_accounts, all_accounts)
        sig_creation_burst = ProvenanceSignals.compute_creation_burst(cluster_accounts)

        # 2. Behavioral Timing Group
        sig_regularity = TimingSignals.compute_interval_regularity(cluster_posts)
        sig_sync_bursts = TimingSignals.compute_synchronized_bursts(cluster_posts)
        sig_interaction = InteractionSignals.compute_interaction_density(
            window_interactions, cluster_member_ids
        )

        # 3. Content Group
        sig_semantic = self.content_engine.compute_semantic_similarity(cluster_posts)
        sig_lexical = ContentSignals.compute_lexical_near_duplicates(cluster_posts)

        # 4. Context Modifier (Never counts toward gate)
        sig_posting_rate = RateSignals.compute_posting_rate(window_posts, cluster_member_ids)

        return {
            # Provenance
            "shared_device": sig_shared_device,
            "shared_ip": sig_shared_ip,
            "creation_burst": sig_creation_burst,
            # Behavioral
            "interval_regularity": sig_regularity,
            "synchronized_bursts": sig_sync_bursts,
            "interaction_density": sig_interaction,
            # Content
            "semantic_similarity": sig_semantic,
            "lexical_near_duplicates": sig_lexical,
            # Context
            "posting_rate": sig_posting_rate,
        }
