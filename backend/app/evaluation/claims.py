"""
Claim Audit Verification Engine for BreachX / HYDRA.
Implements Milestone M21, Sections 19.6, 19.7, and Release Gate 6.
Enforces strict claim validation on marketing text and pitch statements.
"""

from typing import List, Dict, Tuple


FORBIDDEN_PHRASES = [
    "detects all bots",
    "100% accuracy",
    "beats gnns",
    "works on twitter",
    "works on real platforms",
    "unsupervised detection",
    "real-time detection",
    "production ready",
    "immutable blockchain",
]

MANDATORY_DISCLAIMERS = [
    "synthetic-data result",
    "simulated",
]


class ClaimAuditor:
    """
    Audits presentation and documentation texts against Sections 19.6 and 19.7.
    """

    @staticmethod
    def audit_text(text: str) -> Tuple[bool, List[str], List[str]]:
        """
        Scans text for forbidden overclaims and verifies mandatory disclaimers.
        Returns:
            (is_compliant, violations, present_disclaimers)
        """
        lower = text.lower()
        violations = []
        for phrase in FORBIDDEN_PHRASES:
            if phrase in lower:
                violations.append(f"Forbidden overclaim detected: '{phrase}' (§19.6)")

        present_disclaimers = [d for d in MANDATORY_DISCLAIMERS if d in lower]

        is_compliant = len(violations) == 0 and len(present_disclaimers) > 0
        return is_compliant, violations, present_disclaimers
