"""
Event and Scenario Schemas for BreachX / HYDRA.
Follows Platform-Neutral Event Schema (§19.5, §4.2).
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class ActorType(str, Enum):
    BACKGROUND = "background"
    BOT = "bot"
    DECOY_FAN = "decoy_fan"
    DECOY_NEWS = "decoy_news"
    DECOY_NAT = "decoy_nat"
    DECOY_FAMILY = "decoy_family"
    FRAMING_ATTACKER = "framing_attacker"
    HUMAN_TROLL = "human_troll"
    LOW_AND_SLOW = "low_and_slow"


class InteractionType(str, Enum):
    REPLY = "reply"
    REPOST = "repost"
    LIKE = "like"
    FOLLOW = "follow"


class Account(BaseModel):
    account_id: str
    created_at: float  # Unix timestamp in seconds
    ip_range_hash: Optional[str] = None  # Keyed HMAC hash
    device_hash: Optional[str] = None  # Keyed HMAC hash
    declared_language: Optional[str] = "en"
    profile_name: Optional[str] = None


class Post(BaseModel):
    post_id: str
    account_id: str
    timestamp: float
    text: str
    language: Optional[str] = "en"
    hashtags: List[str] = Field(default_factory=list)
    urls: List[str] = Field(default_factory=list)


class Interaction(BaseModel):
    interaction_id: str
    source_id: str
    target_id: str
    interaction_type: InteractionType
    timestamp: float


class GroundTruthLabel(BaseModel):
    account_id: str
    actor_type: ActorType
    is_bot: bool
    is_decoy: bool
    campaign_id: Optional[str] = None


class WindowEvents(BaseModel):
    window_index: int
    start_time: float
    end_time: float
    accounts: List[Account] = Field(default_factory=list)
    posts: List[Post] = Field(default_factory=list)
    interactions: List[Interaction] = Field(default_factory=list)


class SimulationRunData(BaseModel):
    scenario_id: str
    seed: int
    config_hash: str
    total_windows: int
    windows: List[WindowEvents] = Field(default_factory=list)
    # Ground truth is isolated from detection engine
    ground_truth: Dict[str, GroundTruthLabel] = Field(default_factory=dict)
