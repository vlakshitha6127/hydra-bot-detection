# BreachX 2026 / HYDRA: Coordinated Bot Network Detection
**Autonomous Full-Stack Cybersecurity Platform**  
**Specification Version:** v1.7 (Authoritative Precedence: Section 21 > Section 20 > All Other Sections)  
**Dataset Notice (§19.6):** All metrics, evaluations, and populations shown are *synthetic-data results* measured from our deterministic event simulator. Zero raw personal identifiers or unhashed IP addresses are stored at rest.

---

## 1. Executive Summary

Modern coordinated bot networks no longer look like crude single-account spammers. In an adversarial landscape, each bot account can appear individually normal: posting intermittently, paraphrasing text, and rotating proxy IP subnets. Traditional account-level classifiers fail because no individual profile looks egregious, while naive community detectors flag legitimate communities (such as music fan clubs or breaking-news reposters) as botnets.

**BreachX / HYDRA** solves this through five structural guarantees:
1. **Multi-Evidence Non-Compensatory Gate (Invariant I1, §21.1):** Automated user-impacting actions strictly require evidence from at least two independent active groups, one of which **must be Provenance** (shared device hardware or burst signup). Behavior-only coordination is never automatically restricted.
2. **Member-Level Eligibility Rule (§21.12, §21.14):** Cluster-level guilt by association is structurally impossible. An account can only be acted upon if it possesses its own qualifying provenance link to another member in the cluster; otherwise, it remains at State 0 (Observe) with a review flag.
3. **Reversible Graduated Response Ladder (Invariants I2, I3, I6, §8.1):** No state skipping. The system progresses strictly through Observe $\to$ Throttle $\to$ Verification Challenge $\to$ Temporary Restriction. All automated actions carry a Time-To-Live (TTL) and decay towards zero if evidence stops. Permanent bans are human-only.
4. **Exact Counterfactual Explainability (Invariant I4, §11.2):** Because the evidence scoring engine is additive in log-odds units ($L_c$), the contribution of each signal is mathematically exact. For every cluster, the engine re-scores counterfactual states (e.g., *"Without Provenance evidence, this cluster would drop to State 0"*).
5. **Cryptographic Tamper-Evident Audit Log (Invariant I7, §18.3):** Every decision is logged in an append-only SHA-256 hash chain ($h_i = \text{SHA256}(h_{i-1} \parallel \text{canonical\_json}(record_i))$) with interactive verification that pinpoints the exact corrupted index if altered.

---

## 2. System Architecture

```text
breach/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI application entrypoint (serves API & Dashboard)
│   │   ├── api/routes.py         # Documented REST API endpoints
│   │   ├── core/security.py      # HMAC-SHA256 keyed hashing & data minimization (M13, I8)
│   │   ├── schemas/              # Pydantic schemas for events, graph, scoring, policy
│   │   ├── simulator/            # Deterministic simulator (M1), populations, attacker (M8)
│   │   ├── signals/              # Provenance, Behavioral, Content, Interaction, Rate signals (M2)
│   │   ├── graph/                # Account graph, rarity weighting, NetworkX Louvain (M3)
│   │   ├── scoring/              # Null percentile normalization, calibration, gate (M4)
│   │   ├── policy/               # State machine, member eligibility, review queue (M5, M22)
│   │   ├── explainability/       # Evidence cards, decoy explanation, counterfactuals (M6)
│   │   ├── audit/                # SHA-256 hash chaining, canonical JSON, tamper verifier (M14)
│   │   └── evaluation/           # Pipeline runner, ablation matrix, baselines (M9, M20, M21)
│   ├── tests/                    # 41 automated unit, invariant, and integration tests
│   └── requirements.txt
├── frontend/                     # React + TypeScript + Vite + Tailwind CSS + Cytoscape.js
│   ├── src/
│   │   ├── components/           # NetworkGraph, EvidencePanel, AuditTimeline, EvaluationView
│   │   ├── api/client.ts         # Typed API client
│   │   └── App.tsx               # Primary Cybersecurity SOC Dashboard
├── docs/                         # Requirements matrix, plan, validation, threat model, demo script
├── start.bat                     # Windows batch one-click runner
├── start.ps1                     # PowerShell launch script
└── README.md
```

---

## 3. Quickstart & How to Run

### Prerequisites
- Python 3.11+
- Node.js v18+ and npm (only needed if rebuilding the frontend)

### One-Click Launch (Windows)
Double-click `start.bat` or run in PowerShell:
```powershell
.\start.ps1
```
This automatically starts the FastAPI engine on `http://127.0.0.1:8000` and opens the Interactive Cybersecurity Dashboard in your default browser.

### Manual Backend Launch
```bash
# In workspace root:
py -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```
- Interactive Operations Dashboard: `http://127.0.0.1:8000/`
- OpenAPI Swagger Documentation: `http://127.0.0.1:8000/docs`

### Running the Automated Test Suite
To execute all 41 unit, property, and invariant tests:
```bash
py -m pytest backend/tests/ -v
```

---

## 4. Pre-Built Benchmark Scenarios (§4.5, §18.8)

| Scenario ID | Name | Description | Authoritative Expected Outcome |
|---|---|---|---|
| **S1** | **Clean Baseline** | Background users + Fan community + News feeds + Campus NAT. | **Zero restrictive actions** on all accounts (§21.10). |
| **S2** | **Naive Bot Farm** | 40 bots sharing devices, burst posting, and templated text. | Escalates through Observe $\to$ Throttle $\to$ Challenge. |
| **S3** | **Evasive Bot Farm** | High timing jitter, paraphrased text, fewer shared devices. | Reaches Throttle later; cost-of-evasion throughput penalty. |
| **S3b** | **Zero-Provenance Farm** | Zero shared hardware, rotated IPs, organic signup spread. | **Blocked from automated restriction**; routed to Review Queue. |
| **S4** | **Adaptive Attacker** | Attacker script mutates tactics over multiple rounds. | Cost-of-evasion measured: throughput drops by 65%+. |
| **S5** | **Decoy Stress Test** | Decoys made progressively more bot-like one signal at a time. | Measures empirical breaking point without false claims. |
| **S6** | **Weaponized Framing** | Adversary copies legitimate fan keywords to frame them. | **Gate holds:** Fan group remains safe at State 0 (Observe). |

---

## 5. Security Posture & Invariants

- **Invariant I1 (No single-signal restriction):** Requires $\ge 2$ active groups, one of which must be Provenance.
- **Invariant I2 (No single-window restriction):** Requires persistence count $N \ge N_1$.
- **Invariant I3 (Reversibility):** All restrictions have a TTL; risk decays exponentially without fresh evidence.
- **Invariant I4 (Explainability):** Exact additive log-odds attribution and counterfactual recalculation.
- **Invariant I5 (Auditability):** Append-only log recording exact inputs, scores, and rules fired.
- **Invariant I6 (Human-only permanent bans):** System ceiling is State 4 (Human Escalation).
- **Invariant I7 (Tamper-evidence):** SHA-256 hash chaining detects single-field modifications.
- **Invariant I8 (Privacy-by-design):** Keyed HMAC-SHA256 for all IPs and device identifiers; secret key stored outside data store.

---

## 6. Authoritative Demo Walkthrough (3 Minutes)

See [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) for the exact step-by-step presentation script matching Section 21.16.
