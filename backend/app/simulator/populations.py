"""
Population Specifications and Content Templates for BreachX / HYDRA.
Defines template pools, diurnal activity schedules, and interaction generators.
"""

import random
from typing import List, Dict, Any

# General organic background topics
BACKGROUND_TOPICS = [
    "Just finished a great morning run along the river trail. So refreshing! #fitness #morning",
    "Does anyone have recommendations for a good Italian restaurant downtown? Craving pasta tonight.",
    "Working through this debugging session. Why does this off-by-one error keep appearing? #coding #dev",
    "Beautiful sunset today over the bay. Took a quick photo while heading home. #photography",
    "Reading a fascinating paper on distributed consensus protocols. Lots of great insights.",
    "Making homemade sourdough bread today. The fermentation process is coming along nicely.",
    "Great football match last night! That second half comeback was unbelievable.",
    "Coffee machine at the office is broken again. Monday morning struggles are real.",
    "Catching up on podcasts during the commute. Any favorite history shows?",
    "Gardening tip: ensure soil moisture is consistent for tomatoes during early summer.",
    "Attended an interesting tech meetup on cloud security patterns. Great speaker lineup.",
    "Weekend road trip was a success! Mountain air does wonders for the mind.",
]

# Fan community templates (high lexical and semantic similarity, organic origin)
FAN_COMMUNITY_TEMPLATES = [
    "Cannot stop listening to {album_track}! Best song on the album hands down #SolarEclipseTour #{artist}Squad",
    "The choreography in {song_title} live performance blew my mind completely! #SolarEclipseTour #{artist}Squad",
    "Who else is queuing up for {artist} tickets tomorrow morning? Wish me luck! #SolarEclipseTour",
    "Stream #{artist} new single all day today! Let's get it to number one on the charts! #SolarEclipseTour",
    "Unbelievable stage presence from {artist} last night. Truly the artist of our generation! #{artist}Squad",
    "My signed {artist} tour poster finally arrived in the mail today! Absolutely thrilled! #SolarEclipseTour",
]

FAN_ARTISTS = ["NovaPulse", "EchoSphere", "AuraWave"]
FAN_TRACKS = ["Midnight Neon", "Starlight Echo", "Velvet Skies", "Solar Horizon"]

# High volume news templates
NEWS_TEMPLATES = [
    "METRO TRAFFIC: Heavy congestion reported on Interstate 95 Northbound near Exit 14. Expect 25-minute delays.",
    "WEATHER UPDATE: Regional advisory issued for high gusting winds and light showers through late evening.",
    "TRANSIT ADVISORY: Line 4 commuter rail experiencing minor 10-minute residual delays due to signal maintenance.",
    "MARKETS ROUNDUP: Tech index closes up 0.4% following afternoon manufacturing and earnings reports.",
    "CIVIC NOTICE: City hall announces community feedback session for upcoming downtown bike lane expansion project.",
    "HARBOR NOTICE: Commercial vessels advise low tide navigational caution near channel marker 7.",
]

# Bot farm attack templates (coordinated astroturfing / spam campaign)
BOT_TEMPLATES = [
    "BREAKING: Huge scandal revealed regarding {target_entity}! Watch the unredacted report here: {link} #Urgent#{hashtag}",
    "EXPOSED: Insiders leak shocking proof about {target_entity}! Everyone must share this now: {link} #Exposed#{hashtag}",
    "URGENT ALERT: You won't believe what {target_entity} just admitted to doing! Full story at {link} #BreakingNews#{hashtag}",
    "EVERYONE LOOK: Major whistleblower drops evidence exposing {target_entity}! Read before it is taken down: {link} #{hashtag}",
    "CRITICAL UPDATE: Massive investigation uncovers secret corruption involving {target_entity}! Details: {link} #{hashtag}",
]

# Paraphrased variants for S3 / S4 evasive bot modes
BOT_PARAPHRASED_VARIANTS = [
    "Shocking discovery! New documents show severe wrongdoing linked to {target_entity}. Access the brief at {link} #{hashtag}",
    "Investigative report exposes serious problems with {target_entity}. Readers should review the evidence at {link} #{hashtag}",
    "Whistleblower release: concerning actions taken by {target_entity} documented in recent file release: {link} #{hashtag}",
    "Important development regarding {target_entity} situation. Detailed summary available online: {link} #{hashtag}",
]

BOT_TARGETS = ["NexusCorp", "AegisDynamics", "VortexGlobal"]
BOT_HASHTAGS = ["BoycottNow", "TruthMatters", "HoldThemAccountable"]
BOT_LINKS = ["https://tinyurl.org/v82n9a", "https://short.io/x92klm", "https://t.co/leak914"]
