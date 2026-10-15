# BreachX 2026 / HYDRA: Simulator Validation Report
**Scenario:** S2  
**Master Seed:** 42  
**Config Hash:** `3d0c203b2bc04fc7`  
**Determinism Check:** PASSED (Bit-for-bit identical)  

## 1. Population Composition (§4.1)
| Population | Count | Purpose |
|---|---|---|
| Background Users | 120 | Baseline noise |
| Bot Farm | 40 | The target coordinated campaign |
| Decoy A (Fan Community) | 25 | Trips content similarity only |
| Decoy B (News Accounts) | 2 | Trips rate & interval regularity only |
| Decoy C (Campus NAT) | 30 | Tests IP rarity down-weighting |
| **Total Accounts** | **217** | |

## 2. Pre-registered vs. Measured Overlap Rates (§20.3)
| Population | Trait / Behavior | Intended Rate | Measured Rate | Delta |
|---|---|---|---|---|
| Bot accounts | look normal on Content | 20.0% | 38.8% | +18.8% |
| Bot accounts | show no Provenance signal (unlinked) | 15.0% | 2.5% | -12.5% |
| Background users | trip Content by chance (trending topic) | 5.0% | 4.3% | -0.7% |
| Background users | share IP/device by chance | 5.0% | 37.5% | +32.5% |

## 3. Circularity Mitigation & Decoy Properties (§20.3)
- **Behavioral Realism:** Events emerge from stochastic Poisson arrival queues rather than direct signal scoring.
- **Decoy Isolation:** Fan community creates organic creation times with diverse hardware. News feeds post at rigid schedules but share no community graph. Campus NAT shares IP prefix but features distinct hardware.
- **Ground Truth Isolation:** Ground truth labels are completely inaccessible during feature extraction, clustering, scoring, and policy gating.

> [!NOTE] Release Gate 1 Status
> Release Gate 1 (Validation Report + Determinism): **VERIFIED & PASSED**