"""
Deterministic Synthetic Event Generator for BreachX / HYDRA.
Implements Milestone M1, M13, and Sections 4, 18.2, 20.3.
"""

import math
import random
from typing import List, Dict, Tuple, Optional
import numpy as np

from backend.app.schemas.event import (
    Account,
    Post,
    Interaction,
    InteractionType,
    ActorType,
    GroundTruthLabel,
    WindowEvents,
    SimulationRunData,
)
from backend.app.simulator.config import ScenarioConfig, get_scenario_config
from backend.app.simulator.populations import (
    BACKGROUND_TOPICS,
    FAN_COMMUNITY_TEMPLATES,
    FAN_ARTISTS,
    FAN_TRACKS,
    NEWS_TEMPLATES,
    BOT_TEMPLATES,
    BOT_PARAPHRASED_VARIANTS,
    BOT_TARGETS,
    BOT_HASHTAGS,
    BOT_LINKS,
)
from backend.app.core.security import hash_device_id, hash_ip_range


class EventSimulator:
    """
    Simulates a synthetic social network across discrete time windows.
    Generates accounts, posts, and interactions with reproducible pseudo-randomness.
    """

    def __init__(self, config: ScenarioConfig):
        self.config = config
        self.rng = random.Random(config.seed)
        self.np_rng = np.random.RandomState(config.seed)
        self.accounts: Dict[str, Account] = {}
        self.ground_truth: Dict[str, GroundTruthLabel] = {}
        self._post_counter = 0
        self._interaction_counter = 0

    def generate_simulation(self) -> SimulationRunData:
        """
        Executes full simulation run across all windows.
        Returns complete event log with isolated ground truth.
        """
        self._initialize_populations()

        windows_data: List[WindowEvents] = []
        base_start_time = 1776326400.0  # Epoch reference

        for w_idx in range(self.config.total_windows):
            w_start = base_start_time + (w_idx * self.config.window_duration_seconds)
            w_end = w_start + self.config.window_duration_seconds

            posts, interactions = self._generate_window_events(w_idx, w_start, w_end)

            # Active accounts appearing in this window
            active_account_ids = set(p.account_id for p in posts)
            active_account_ids.update(i.source_id for i in interactions)
            active_account_ids.update(i.target_id for i in interactions)
            active_accounts = [self.accounts[aid] for aid in active_account_ids if aid in self.accounts]

            windows_data.append(
                WindowEvents(
                    window_index=w_idx,
                    start_time=w_start,
                    end_time=w_end,
                    accounts=active_accounts,
                    posts=posts,
                    interactions=interactions,
                )
            )

        return SimulationRunData(
            scenario_id=self.config.scenario_id,
            seed=self.config.seed,
            config_hash=self.config.compute_config_hash(),
            total_windows=self.config.total_windows,
            windows=windows_data,
            ground_truth=self.ground_truth,
        )

    def _initialize_populations(self) -> None:
        """
        Creates all account entities with keyed HMAC identifiers.
        """
        self.accounts.clear()
        self.ground_truth.clear()

        # 1. Background Users
        for i in range(self.config.n_background_users):
            aid = f"usr_bg_{i:03d}"
            created_at = 1740000000.0 + self.rng.uniform(0, 30000000.0)

            # ~5% share a subnet/device by chance (Section 20.3)
            if self.rng.random() < self.config.overlap_rates.background_share_infra:
                raw_ip = f"192.168.10.{self.rng.randint(1, 5)}"
                raw_device = f"shared_library_kiosk_{self.rng.randint(1, 2)}"
            else:
                raw_ip = f"198.51.{self.rng.randint(1, 250)}.{self.rng.randint(1, 250)}"
                raw_device = f"device_bg_{aid}_{self.rng.randint(1000, 9999)}"

            self.accounts[aid] = Account(
                account_id=aid,
                created_at=created_at,
                ip_range_hash=hash_ip_range(raw_ip),
                device_hash=hash_device_id(raw_device),
                profile_name=f"User_{i}",
            )
            self.ground_truth[aid] = GroundTruthLabel(
                account_id=aid,
                actor_type=ActorType.BACKGROUND,
                is_bot=False,
                is_decoy=False,
            )

        # 2. Decoy A: Fan Community
        for i in range(self.config.n_fan_accounts):
            aid = f"fan_comm_{i:03d}"
            created_at = 1750000000.0 + self.rng.uniform(0, 15000000.0)
            raw_ip = f"203.0.113.{self.rng.randint(1, 250)}"
            raw_device = f"device_fan_{aid}_{self.rng.randint(1000, 9999)}"

            self.accounts[aid] = Account(
                account_id=aid,
                created_at=created_at,
                ip_range_hash=hash_ip_range(raw_ip),
                device_hash=hash_device_id(raw_device),
                profile_name=f"MusicFan_{i}",
            )
            self.ground_truth[aid] = GroundTruthLabel(
                account_id=aid,
                actor_type=ActorType.DECOY_FAN,
                is_bot=False,
                is_decoy=True,
            )

        # 3. Decoy B: News Account(s)
        for i in range(self.config.n_news_accounts):
            aid = f"news_feed_{i:02d}"
            created_at = 1735000000.0 + (i * 100000.0)
            raw_ip = f"198.18.0.{i+1}"
            raw_device = f"automated_server_news_{i}"

            self.accounts[aid] = Account(
                account_id=aid,
                created_at=created_at,
                ip_range_hash=hash_ip_range(raw_ip),
                device_hash=hash_device_id(raw_device),
                profile_name=f"MetroNews_{i}",
            )
            self.ground_truth[aid] = GroundTruthLabel(
                account_id=aid,
                actor_type=ActorType.DECOY_NEWS,
                is_bot=False,
                is_decoy=True,
            )

        # 4. Decoy C: Campus/Office NAT
        campus_ip = "192.0.2.1"  # Common subnet for all campus accounts
        for i in range(self.config.n_nat_accounts):
            aid = f"campus_nat_{i:03d}"
            created_at = 1745000000.0 + self.rng.uniform(0, 20000000.0)
            raw_device = f"device_student_{i}_{self.rng.randint(1000, 9999)}"

            self.accounts[aid] = Account(
                account_id=aid,
                created_at=created_at,
                ip_range_hash=hash_ip_range(campus_ip),  # Shared IP
                device_hash=hash_device_id(raw_device),  # Distinct devices
                profile_name=f"Student_{i}",
            )
            self.ground_truth[aid] = GroundTruthLabel(
                account_id=aid,
                actor_type=ActorType.DECOY_NAT,
                is_bot=False,
                is_decoy=True,
            )

        # 5. Bot Farm (Target Campaign)
        if self.config.n_bot_accounts > 0:
            farm_creation_base = 1776300000.0  # Tight creation burst
            devices = [f"botnet_shared_hardware_{d}" for d in range(self.config.bot_shared_devices_count)]
            ip_pool = [f"203.0.120.{idx}" for idx in range(max(1, self.config.bot_shared_devices_count // 2))]

            for i in range(self.config.n_bot_accounts):
                aid = f"bot_act_{i:03d}"

                # Noise check: 15% have no shared device/burst signup (§20.3)
                is_isolated_provenance = (
                    self.config.provenance_evasion_mode == "full"
                    or (self.rng.random() < self.config.overlap_rates.bot_no_provenance)
                )

                if is_isolated_provenance:
                    created_at = 1740000000.0 + self.rng.uniform(0, 25000000.0)
                    raw_ip = f"198.51.100.{self.rng.randint(1, 254)}"
                    raw_device = f"evasive_independent_device_{i}"
                else:
                    # Injected creation burst (Poisson/normal cluster within minutes)
                    created_at = farm_creation_base + self.rng.gauss(0, 300.0)
                    raw_device = devices[i % len(devices)]
                    raw_ip = ip_pool[i % len(ip_pool)]

                self.accounts[aid] = Account(
                    account_id=aid,
                    created_at=created_at,
                    ip_range_hash=hash_ip_range(raw_ip),
                    device_hash=hash_device_id(raw_device),
                    profile_name=f"Bot_{i}",
                )
                self.ground_truth[aid] = GroundTruthLabel(
                    account_id=aid,
                    actor_type=ActorType.BOT,
                    is_bot=True,
                    is_decoy=False,
                    campaign_id="campaign_alpha",
                )

    def _generate_window_events(
        self, window_idx: int, w_start: float, w_end: float
    ) -> Tuple[List[Post], List[Interaction]]:
        """
        Generates posts and interactions for a single time window.
        """
        posts: List[Post] = []
        interactions: List[Interaction] = []

        # 1. Background Users: Diurnal rate
        # Diurnal modulation curve (sinusoidal peak during middle of day)
        hour = (window_idx * 1) % 24
        diurnal_factor = 0.3 + 0.7 * max(0.0, math.sin(math.pi * hour / 24.0))

        for aid, acc in self.accounts.items():
            if not aid.startswith("usr_bg"):
                continue
            # Poisson arrival for posts
            expected_posts = 0.5 * diurnal_factor
            num_posts = self.np_rng.poisson(expected_posts)
            for _ in range(num_posts):
                p_time = w_start + self.rng.uniform(0, self.config.window_duration_seconds)
                # Overlap check: 5% background trip content by chance
                if self.rng.random() < self.config.overlap_rates.background_trip_content:
                    text = f"Loving this trending vibe today! #SolarEclipseTour #{self.rng.choice(FAN_ARTISTS)}Squad"
                    ht = ["SolarEclipseTour"]
                else:
                    text = self.rng.choice(BACKGROUND_TOPICS)
                    ht = [t.strip("#") for t in text.split() if t.startswith("#")]

                self._post_counter += 1
                posts.append(
                    Post(
                        post_id=f"pst_{self._post_counter:06d}",
                        account_id=aid,
                        timestamp=p_time,
                        text=text,
                        hashtags=ht,
                    )
                )

        # 2. Decoy A: Fan Community (High content & hashtag similarity)
        for aid, acc in self.accounts.items():
            if not aid.startswith("fan_comm"):
                continue
            # Organic event excitement causes burst in fan community
            if self.rng.random() < 0.6:
                tmpl = self.rng.choice(FAN_COMMUNITY_TEMPLATES)
                text = tmpl.format(
                    album_track=self.rng.choice(FAN_TRACKS),
                    song_title=self.rng.choice(FAN_TRACKS),
                    artist=self.rng.choice(FAN_ARTISTS),
                )
                p_time = w_start + self.rng.uniform(0, self.config.window_duration_seconds)
                self._post_counter += 1
                posts.append(
                    Post(
                        post_id=f"pst_{self._post_counter:06d}",
                        account_id=aid,
                        timestamp=p_time,
                        text=text,
                        hashtags=["SolarEclipseTour", "MusicCommunity"],
                    )
                )

        # 3. Decoy B: News Account (Clockwork regular intervals, high volume)
        for aid, acc in self.accounts.items():
            if not aid.startswith("news_feed"):
                continue
            # Exactly 4 posts per hour, scheduled every 900s
            for step in range(4):
                p_time = w_start + (step * 900.0) + self.rng.uniform(-5.0, 5.0)
                text = self.rng.choice(NEWS_TEMPLATES)
                self._post_counter += 1
                posts.append(
                    Post(
                        post_id=f"pst_{self._post_counter:06d}",
                        account_id=aid,
                        timestamp=p_time,
                        text=text,
                        hashtags=["NewsUpdate", "Metro"],
                    )
                )

        # 4. Decoy C: Campus NAT
        for aid, acc in self.accounts.items():
            if not aid.startswith("campus_nat"):
                continue
            if self.rng.random() < 0.3:
                p_time = w_start + self.rng.uniform(0, self.config.window_duration_seconds)
                text = self.rng.choice(BACKGROUND_TOPICS)
                self._post_counter += 1
                posts.append(
                    Post(
                        post_id=f"pst_{self._post_counter:06d}",
                        account_id=aid,
                        timestamp=p_time,
                        text=text,
                        hashtags=[],
                    )
                )

        # 5. Bot Farm (Active starting at bot_campaign_active_from_window)
        if window_idx >= self.config.bot_campaign_active_from_window and self.config.n_bot_accounts > 0:
            burst_center = w_start + (self.config.window_duration_seconds * 0.4)
            bot_posts = []

            for aid, acc in self.accounts.items():
                if not aid.startswith("bot_act"):
                    continue

                # Jitter & timing: tight synchrony vs. evasive jitter
                noise_behavior = self.rng.random() < self.config.overlap_rates.bot_normal_on_behavioral
                if noise_behavior:
                    p_time = w_start + self.rng.uniform(0, self.config.window_duration_seconds)
                else:
                    jitter = self.config.bot_timing_jitter * 1800.0
                    p_time = burst_center + self.rng.gauss(0, max(5.0, jitter))

                # Content selection: S6 framing vs template vs paraphrase vs normal noise
                noise_content = self.rng.random() < self.config.overlap_rates.bot_normal_on_content

                if self.config.is_framing_attack:
                    # S6 Framing Attack: Bot maliciously copies Fan Community's hashtags and keywords!
                    text = f"ATTENTION: {self.rng.choice(FAN_ARTISTS)} concert scandal! Must read now: {self.rng.choice(BOT_LINKS)} #SolarEclipseTour #{self.rng.choice(FAN_ARTISTS)}Squad"
                    ht = ["SolarEclipseTour", "FramingTarget"]
                elif noise_content:
                    text = self.rng.choice(BACKGROUND_TOPICS)
                    ht = []
                elif self.rng.random() < self.config.bot_paraphrase_rate:
                    # Paraphrased evasive mode (S3)
                    tmpl = self.rng.choice(BOT_PARAPHRASED_VARIANTS)
                    text = tmpl.format(
                        target_entity=self.rng.choice(BOT_TARGETS),
                        link=self.rng.choice(BOT_LINKS),
                        hashtag=self.rng.choice(BOT_HASHTAGS),
                    )
                    ht = [self.rng.choice(BOT_HASHTAGS)]
                else:
                    # Obvious templated spam (S2)
                    tmpl = self.rng.choice(BOT_TEMPLATES)
                    text = tmpl.format(
                        target_entity=self.rng.choice(BOT_TARGETS),
                        link=self.rng.choice(BOT_LINKS),
                        hashtag=self.rng.choice(BOT_HASHTAGS),
                    )
                    ht = [self.rng.choice(BOT_HASHTAGS)]

                self._post_counter += 1
                p = Post(
                    post_id=f"pst_{self._post_counter:06d}",
                    account_id=aid,
                    timestamp=p_time,
                    text=text,
                    hashtags=ht,
                )
                posts.append(p)
                bot_posts.append(p)

            # Generate synchronized reciprocal interactions between bot accounts
            if len(bot_posts) > 1 and not self.config.provenance_evasion_mode == "full":
                for i in range(len(bot_posts)):
                    target_p = bot_posts[(i + 1) % len(bot_posts)]
                    self._interaction_counter += 1
                    interactions.append(
                        Interaction(
                            interaction_id=f"itr_{self._interaction_counter:06d}",
                            source_id=bot_posts[i].account_id,
                            target_id=target_p.account_id,
                            interaction_type=InteractionType.REPOST,
                            timestamp=target_p.timestamp + self.rng.uniform(1.0, 15.0),
                        )
                    )

        # Background sparse interactions
        bg_posts = [p for p in posts if p.account_id.startswith("usr_bg")]
        if len(bg_posts) > 2:
            for _ in range(min(15, len(bg_posts) // 2)):
                src = self.rng.choice(bg_posts)
                tgt = self.rng.choice(bg_posts)
                if src.account_id != tgt.account_id:
                    self._interaction_counter += 1
                    interactions.append(
                        Interaction(
                            interaction_id=f"itr_{self._interaction_counter:06d}",
                            source_id=src.account_id,
                            target_id=tgt.account_id,
                            interaction_type=InteractionType.LIKE,
                            timestamp=max(src.timestamp, tgt.timestamp) + self.rng.uniform(50.0, 600.0),
                        )
                    )

        # Sort chronologically
        posts.sort(key=lambda p: p.timestamp)
        interactions.sort(key=lambda i: i.timestamp)

        return posts, interactions
