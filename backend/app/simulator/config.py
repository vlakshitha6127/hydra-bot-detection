"""
Scenario Configurations and Constants for BreachX / HYDRA.
Defines Scenarios S1-S6 (§4.5, §18.8) and Pre-registered Overlap Rates (§20.3, T9).
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import hashlib
import json


class OverlapRatesConfig(BaseModel):
    """
    Pre-registered overlap rates from Section 20.3 (frozen before evaluation).
    """
    bot_normal_on_content: float = 0.20  # 20% of bots use varied/organic content
    bot_normal_on_behavioral: float = 0.20  # 20% of bots use jittered intervals
    bot_no_provenance: float = 0.15  # 15% of bots have separate device/IP (S3b leak)
    background_trip_content: float = 0.05  # 5% of background users post trending hashtags
    background_trip_behavioral: float = 0.05  # 5% of background users have regular schedules
    background_share_infra: float = 0.05  # 5% of background users share home/campus IPs/devices


class ScenarioConfig(BaseModel):
    scenario_id: str
    name: str
    description: str
    seed: int = 42
    total_windows: int = 10
    window_duration_seconds: float = 3600.0  # 1 hour per window

    # Population sizing
    n_background_users: int = 120
    n_bot_accounts: int = 40
    n_fan_accounts: int = 25
    n_news_accounts: int = 2
    n_nat_accounts: int = 30

    # Overlap configuration
    overlap_rates: OverlapRatesConfig = Field(default_factory=OverlapRatesConfig)

    # Attacker specifics for scenarios
    bot_campaign_active_from_window: int = 2
    bot_shared_devices_count: int = 4  # Bots share among 4 devices
    bot_timing_jitter: float = 0.05  # Tight synchrony by default (S2)
    bot_paraphrase_rate: float = 0.1  # Low paraphrase by default (S2)

    # Special scenario flags
    is_framing_attack: bool = False  # S6
    decoy_stress_level: float = 0.0  # S5
    provenance_evasion_mode: str = "none"  # "none", "partial", "full"

    def compute_config_hash(self) -> str:
        dump = self.model_dump_json()
        return hashlib.sha256(dump.encode("utf-8")).hexdigest()[:16]


def get_scenario_config(scenario_id: str, seed: int = 42) -> ScenarioConfig:
    """
    Returns pre-built scenario configurations (§4.5, §18.8).
    """
    if scenario_id == "S1":
        return ScenarioConfig(
            scenario_id="S1",
            name="S1 Baseline (Clean / Decoys Only)",
            description="Background users + legitimate decoys (fan community, news accounts, campus NAT). Zero bot activity. Expect zero restrictive actions.",
            seed=seed,
            n_bot_accounts=0,
            bot_campaign_active_from_window=999,
        )
    elif scenario_id == "S2":
        return ScenarioConfig(
            scenario_id="S2",
            name="S2 Naive Bot Farm",
            description="Bot farm with obvious coordination signals: shared devices, synchronized posting bursts, templated near-duplicate posts.",
            seed=seed,
            n_bot_accounts=40,
            bot_campaign_active_from_window=2,
            bot_shared_devices_count=4,
            bot_timing_jitter=0.05,
            bot_paraphrase_rate=0.05,
        )
    elif scenario_id == "S3":
        # S3a: partial provenance leak (§21.12)
        return ScenarioConfig(
            scenario_id="S3",
            name="S3 Evasive Bot Farm",
            description="Evasive farm: higher timing jitter, paraphrased content, slower signups, and partial device rotation.",
            seed=seed,
            n_bot_accounts=40,
            bot_campaign_active_from_window=2,
            bot_shared_devices_count=12,
            bot_timing_jitter=0.45,
            bot_paraphrase_rate=0.65,
            provenance_evasion_mode="partial",
        )
    elif scenario_id == "S3b":
        # S3b: zero provenance farm (§21.12)
        return ScenarioConfig(
            scenario_id="S3b",
            name="S3b Zero-Provenance Evasive Farm",
            description="Zero shared devices, spread-out signup, fully rotated IPs. Expected: blocked from automated states, routed to review queue.",
            seed=seed,
            n_bot_accounts=40,
            bot_campaign_active_from_window=2,
            bot_shared_devices_count=40,  # Each bot has unique device
            bot_timing_jitter=0.45,
            bot_paraphrase_rate=0.65,
            provenance_evasion_mode="full",
        )
    elif scenario_id == "S4":
        return ScenarioConfig(
            scenario_id="S4",
            name="S4 Adaptive Attacker",
            description="Attacker script that adaptively mutates tactics over multiple rounds as defender takes actions.",
            seed=seed,
            n_bot_accounts=40,
            bot_campaign_active_from_window=2,
        )
    elif scenario_id == "S5":
        return ScenarioConfig(
            scenario_id="S5",
            name="S5 Decoy Stress Test",
            description="Legitimate decoys pushed progressively more bot-like one signal at a time to measure breaking point.",
            seed=seed,
            n_bot_accounts=30,
            decoy_stress_level=0.5,
        )
    elif scenario_id == "S6":
        return ScenarioConfig(
            scenario_id="S6",
            name="S6 Framing Attack (Weaponized Detection)",
            description="Adversary attempts to frame legitimate fan community by copying their keywords and timing without shared provenance.",
            seed=seed,
            n_bot_accounts=35,
            is_framing_attack=True,
            bot_campaign_active_from_window=2,
        )
    elif scenario_id == "S7":
        return ScenarioConfig(
            scenario_id="S7",
            name="S7 Low-and-Slow Bot Campaign",
            description="Low-event-rate bot farm designed to evade volume thresholds by posting infrequently with wide jitter and distributed devices.",
            seed=seed,
            n_bot_accounts=35,
            bot_campaign_active_from_window=1,
            bot_shared_devices_count=10,
            bot_timing_jitter=0.60,
            bot_paraphrase_rate=0.50,
        )
    elif scenario_id == "S8":
        return ScenarioConfig(
            scenario_id="S8",
            name="S8 Coordinated Human Trolls (Mixed Actors)",
            description="Human troll flock coordinated on hashtags and timing bursts without shared hardware provenance. Tests non-compensatory gate against false positives.",
            seed=seed,
            n_bot_accounts=0,
            n_fan_accounts=45,
            decoy_stress_level=0.7,
        )
    elif scenario_id == "S9":
        return ScenarioConfig(
            scenario_id="S9",
            name="S9 Heterogeneous Farm Sweep",
            description="Multi-adversary sweep featuring naive bots alongside evasive and framing cells simultaneously.",
            seed=seed,
            n_bot_accounts=50,
            bot_campaign_active_from_window=2,
            bot_shared_devices_count=6,
            bot_timing_jitter=0.25,
            bot_paraphrase_rate=0.35,
        )
    else:
        # Default fallback
        return ScenarioConfig(scenario_id=scenario_id, name=f"Scenario {scenario_id}", description="Custom Scenario", seed=seed)
