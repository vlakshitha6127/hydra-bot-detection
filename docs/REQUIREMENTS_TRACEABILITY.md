# BreachX 2026 / HYDRA: Requirements Traceability Matrix
**Specification Version:** v1.7 (Authoritative Precedence: Section 21 > Section 20 > All Other Sections)  
**Last Updated:** 2026-10-14  

---

## 1. System Invariants (Sections 2, 18, 21)

| ID | Invariant Requirement | Enforcement Mechanism | Implementation Target | Verification Test | Status |
|---|---|---|---|---|---|
| **I1** | **No restrictive action from a single signal** | Policy engine strictly requires evidence from $\ge 2$ active evidence groups, one of which **must** be Provenance for states 1–3 ($21.1, 7.3$). | `backend/app/policy/engine.py` | `tests/test_invariants.py::test_i1_no_single_signal_restriction` | VERIFIED |
| **I2** | **No restrictive action from a single time window** | Policy engine enforces consecutive window persistence count $N \ge N_1$ before state transition ($7.4, 8.1$). | `backend/app/policy/engine.py` | `tests/test_invariants.py::test_i2_persistence_requirement` | VERIFIED |
| **I3** | **All automated actions are reversible** | Every restriction carries a Time-To-Live (TTL); risk score $R_c$ decays with parameter $\lambda \in (0, 1)$ without fresh evidence ($7.4, 8.2$). | `backend/app/policy/engine.py`, `backend/app/scoring/temporal.py` | `tests/test_invariants.py::test_i3_ttl_and_decay_reversibility` | VERIFIED |
| **I4** | **Every decision is explainable** | Scoring model is additive in log-odds units ($L_c = \text{prior} + \sum e_s$); contributions are exact; counterfactuals recomputed by exact re-scoring ($7.1, 11.2$). | `backend/app/explainability/explainer.py` | `tests/test_explainability.py::test_exact_additivity_and_counterfactuals` | VERIFIED |
| **I5** | **Every decision is auditable** | Append-only decision log recording window, cluster_id, account_id, signals, $L_c, R_c, A_c$, rule fired, state transition ($8.3, 18.3$). | `backend/app/audit/audit_log.py` | `tests/test_audit.py::test_decision_audit_logging` | VERIFIED |
| **I6** | **Permanent decisions are human-only** | Automated response ladder caps strictly at State 3 (Temporary Restriction) and State 4 (Human Escalation). Permanent ban cannot be issued by automation ($8.1, 18.1$). | `backend/app/policy/engine.py` | `tests/test_invariants.py::test_i6_no_automated_permanent_action` | VERIFIED |
| **I7** | **Tamper-evident audit log** | Cryptographic SHA-256 hash chain: $h_i = \text{SHA256}(h_{i-1} \parallel \text{canonical\_json}(record_i))$; verification function detects first modified record index ($18.3, \text{M14a}$). | `backend/app/audit/hasher.py` | `tests/test_audit.py::test_tamper_detection_at_exact_index` | VERIFIED |
| **I8** | **No raw identifiers stored at rest** | Raw device fingerprints and IP ranges are transformed into keyed HMAC-SHA256 hashes using a separate secret key outside the data store ($18.2, \text{M13}$). | `backend/app/core/security.py` | `tests/test_security.py::test_no_raw_identifiers_in_storage` | VERIFIED |
| **I9** | **Appeals and recovery path** (Stretch, Tier 3) | Restricted account can trigger appeal with step-up verification ($18.6, \text{M16}$). | `backend/app/policy/appeals.py` | `tests/test_appeals.py` | TIER 3 / STRETCH |

---

## 2. Authoritative Rules from Section 21

| Rule ID | Section | Exact Specification Requirement | Implementation Target | Test Target | Status |
|---|---|---|---|---|---|
| **R-GATE-1** | 21.1, 21.12 | **Evidence Groups Gate:** States 1–3 require active group count $A_c \ge 2$, where one group **must** be Provenance. Behavior-only clusters remain at State 0 (Observe) and queue to human review. | `backend/app/scoring/gate.py` | `tests/test_gate.py::test_provenance_gate_rule` | VERIFIED |
| **R-MEMB-1** | 21.12, 21.14 | **Member-Level Eligibility:** User-impacting automated action on an account requires the account itself has a direct provenance link (shared device or rare shared-IP) to another cluster member. Ineligible members remain at Observe + review flag. Cluster state is median over eligible members. | `backend/app/policy/engine.py` | `tests/test_policy.py::test_eligible_member_and_mixed_cluster` | VERIFIED |
| **R-OUTPUT-1**| 21.14 | **Three Separate Logged Outputs:** Must never merge: (1) evidence score (log-odds), (2) evidence gate (active groups & member eligibility), (3) policy decision (ladder state). | `backend/app/schemas/decision.py`, `backend/app/audit/audit_log.py` | `tests/test_schemas.py::test_three_separate_outputs` | VERIFIED |
| **R-CORR-1** | 21.1, 21.15 | **Correlation & Common-Cause:** Compute pairwise rank correlation between families across windows and clusters. If correlation is high, merge before gating or raise threshold. Common-cause test ensures single hidden cause does not fool gate. | `backend/app/scoring/correlation.py` | `tests/test_gate.py::test_common_cause_synthetic` | VERIFIED |
| **R-SCOR-1** | 21.9 | **Default Calibration & Scoring:** Normalization $x_s(c)$ via background null percentile. Calibration $f_s(x) = \max(0, (x - x0_s)/(1 - x0_s))$, $x0_s \approx 0.9$. Group evidence $E_g = \sum e_s$ capped at $E_{\max}$. $L_c = \sum \text{capped}(E_g)$. | `backend/app/scoring/calibrator.py` | `tests/test_scoring.py::test_scoring_calibration_and_caps` | VERIFIED |
| **R-TEMP-1** | 7.4, 21.3 | **Temporal Accumulation:** Moving-average $R_c(t) = \text{decay} \cdot R_c(t-1) + (1-\text{decay}) \cdot L_c(t)$. Cluster identity tracking by member Jaccard overlap $\ge \theta_J$ or per-account median default. | `backend/app/scoring/temporal.py` | `tests/test_temporal.py::test_temporal_decay_and_hysteresis` | VERIFIED |
| **R-LADD-1** | 8.1, 8.2 | **Graduated Response Ladder:** States 0 (Observe), 1 (Throttle), 2 (Verification challenge), 3 (Temporary restriction TTL), 4 (Human escalation). One step at a time; no state skipping. Hysteresis de-escalation. | `backend/app/policy/engine.py` | `tests/test_policy.py::test_no_state_skipping_and_hysteresis` | VERIFIED |
| **R-REVQ-1** | 21.8, M22 | **Review Queue Ranking:** Coordination score $C_c = \text{capped}(E_{\text{Behavioral}}) + \text{capped}(E_{\text{Content}})$. Ranked by $C_c$, ties broken by persistence, then size. Rate-limited to top $K$ per window. Precision@k evaluation. | `backend/app/policy/review_queue.py` | `tests/test_review_queue.py::test_ranking_and_rate_limit` | VERIFIED |
| **R-DECOY-1**| 21.10, 21.12 | **Decoy Safety Guarantee:** Zero user-impacting actions on Decoys A, B, C in S1. S5 breaking point analysis. Decoy F (legitimate provenance overlap) evaluated with pre-committed mitigation. | `backend/app/evaluation/suite.py` | `tests/test_evaluation.py::test_s1_zero_decoy_restrictions` | VERIFIED |
| **R-CLAIM-1**| 19.6, 21.10 | **Claim Discipline:** Label all metrics as synthetic-data results. Report held-out vs tuning results separately. Never claim 100% detection or real-world validity. | `backend/app/evaluation/claims.py` | `tests/test_claims.py::test_claim_audit` | VERIFIED |

---

## 3. Tiered Implementation Scope (Sections 20, 21.13)

### Tier 0: Functional Detection Core (Immediate MVP)
- **M1:** Deterministic Simulator + ground truth + S1/S2 + validation report ($20.3$).
- **M13:** Keyed-hash identifiers (HMAC-SHA256) built into data model from day one.
- **M2 (T0):** Three evidence groups:
  1. *Provenance:* Shared device fingerprint.
  2. *Behavioral:* Posting-interval regularity, synchronized posting.
  3. *Content:* Semantic similarity (embeddings / TF-IDF cosine fallback).
- **M3:** Account graph, rarity weighting ($1/\log(1+n)$), NetworkX weighted Louvain clustering with fixed seed.
- **M4:** Evidence scoring, calibration map, group caps, gate rule ($A_c \ge 2$ with Provenance), per-account state default.
- **M5:** Policy state machine (States 0–4), no state skipping, reversible TTL/decay, eligible-member check, mixed-cluster safety.
- **M6:** Structured evidence cards for Decoy (refusal) and Bot Farm (escalation) + exact counterfactuals.
- **M8 (Scripted):** Scripted attacker schedule.
- **Exit Check:** S1 produces zero restrictions; S2 farm escalates; eligible-member test passes; determinism confirmed.

### Tier 1: Complete Core System (Must Ship)
- **M2 (Full):** Additional signals:
  - Identity: Shared IP range (rarity down-weighted).
  - Creation timing: Signup burst (Poisson surprise vs null).
  - Content: Lexical near-duplicate (MinHash / Jaccard shingles).
  - Interaction: Interaction timing / reciprocity.
  - Context: Posting rate (modifier only, never gate-satisfying).
- **M12:** Threat model document (STRIDE) + Scenario S6 (Framing attack simulation and test).
- **M14a:** Append-only SHA-256 hash-chained audit log with integrity verification API.
- **M14b:** Interactive tamper test demo (detects exact corrupted record index).
- **M22:** Rate-limited review queue ($K=5$) with coordination score $C_c$ and Precision@k evaluation.
- **M8 (Full):** Cost-of-evasion metrics: primary = throughput retained, secondary = reach retained, distinct devices/IPs required.
- **M9:** Automated ablation matrix (all signal families toggled across S2–S5), plus lightweight baselines (content-only, graph-only).
- **M7:** Interactive cybersecurity dashboard (React + Vite + Tailwind + Cytoscape.js/ReactFlow + Recharts) covering:
  1. Cluster graph with state halo & node inspection.
  2. Evidence card with contribution bars & counterfactuals.
  3. Decoy explanation panel ("gate refused").
  4. Response ladder & audit log timeline with verify/tamper button.
  5. Scenario controls (S1–S6, seed selector, step/play/reset).
  6. Ground-truth judge toggle (off by default).
- **M11:** Demo hardening (pre-computed scenario caches, reproducible 3-minute demo script, health checks).

### Tier 2: Realism & Benchmarks (If Time Allows)
- **M20:** Baselines (Per-account bot score classifier, Content-only, Graph-only) with comparison table.
- **M18:** Realism populations (Low-and-slow bots, partially automated accounts, human trolls, delayed posters, Decoy D activists, Decoy E breaking news) & Scenarios S7–S9.
- **M10:** Real-data sanity check feasibility analysis and schema adapter.

### Tier 3: Cut / Stretch Goals
- **M15:** Honeypot / Canary (Trap family).
- **M16:** Challenge cost model and appeals flow ($I9$).
- **M17:** Multi-scale time windows ($1\text{h}, 1\text{d}, 7\text{d}$) with max-evidence combination rule.
- **M19:** Multilingual content generation and multilingual embeddings.
- **M21:** Formal cross-platform schema adapter.

---

## 4. [VERIFY] Checklist (Section 21.11)

| ID | Item | Spec Ref | Description & Acceptance Criteria | Verification Result |
|---|---|---|---|---|
| **V1** | NetworkX Louvain API | 6.3 | Test `networkx.algorithms.community.louvain_communities` with `weight`, `resolution`, `seed`. Output must be identical across repeated runs. | VERIFIED in Python 3.11 |
| **V2** | Embedding Model Choice | 5, 14 | Model `all-MiniLM-L6-v2` via `sentence-transformers` or lightweight local deterministic sentence embedder fallback when offline. Measure latency & separation. | VERIFIED with local fallback |
| **V3** | MinHash / Shingle Library | 5 | Verify `datasketch` or deterministic k-shingle MinHash for Jaccard similarity. Detects known near-duplicate pairs. | VERIFIED |
| **V4** | Creation-burst test & null model | 5, 21.9 | Flags injected burst; background scores unremarkable under null. | VERIFIED |
| **V5** | Keyed-hash design review | 18.2 | HMAC-SHA256 for IP & device IDs; secret key held outside data store; raw values never stored. | VERIFIED |
| **V6** | LLM access & cost for attacker | 10.1 | Scripted schedule is primary; LLM layer is optional/cached. Verify zero external dependencies required for core run. | VERIFIED |
| **V7** | Public dataset feasibility | 9.4, 21.7 | Document Cresci / TwiBot-22 fields, licenses, and missing IP/device data. | VERIFIED (Tier 2/Doc) |
| **V8** | Frontend and graph library | 14 | Cytoscape.js / React Flow in Vite React TypeScript app. Smooth layout rendering. | VERIFIED |
| **V9** | Related-work sources | 19.7 | Verify academic citations (Rauchfleisch & Kaiser 2020; Pacheco et al.; Vargas et al.). | VERIFIED in docs |
| **V10**| Signing library (M14b) | 18.3 | Ed25519 or HMAC checkpoint signature round-trip test. | VERIFIED |
| **V11**| Framework identifiers | 18.7 | OWASP Automated Threats / DISARM mapping documentation. | VERIFIED in docs |

---

## 5. [TUNE] Checklist (Section 21.11)

| ID | Parameter / Item | Spec Ref | Description & Initial Frozen Values | Tuning & Validation Method |
|---|---|---|---|---|
| **T1** | Window Length | 3 | Window size in events / simulated hours (Default: 100 events or 1 simulated hour per window). | Calibrated on tuning seed 42 |
| **T2** | Normalization, Weights, Caps | 7.1, 21.9 | $x0_s = 0.9$, Weights $w_s = 1.0$ (Identity/Device: 1.5, Timing: 1.0, Content: 1.2), $E_{\max} = 5.0$, prior = 0.0. | Logistic fit / grid search on tuning seeds |
| **T3** | Group Thresholds & Gate Params | 7.2, 21.1 | Group active threshold: Provenance $\ge 1.0$, Behavioral $\ge 1.2$, Content $\ge 1.2$. Active groups $A_c \ge 2$. | Constrained to zero user-impacting actions on decoys |
| **T4** | Ladder Thresholds, Persistence, Decay | 7.4, 8.1 | $T_1 = 2.0, T_2 = 3.5, T_3 = 5.0$. Persistence $N_1 = 2, N_2 = 3, N_3 = 4$. Decay $\lambda = 0.8$. Hysteresis exit: $T - 0.5$. | Detection delay vs false positive trade-off |
| **T5** | Louvain Resolution & Cluster Filters | 6.3 | Resolution $\gamma = 1.0$. Min cluster size = 3, min edge density = 0.2. | Resolution sweep stability |
| **T6** | Rarity Weighting Form | 6.2 | Attribute edge weight: $w_{\text{rarity}} = 1.0 / \log_2(2 + n_{\text{shared}})$. | Verifies Campus NAT ($n=50$) edge $\ll$ Device ($n=2$) edge |
| **T7** | Cluster-matching Threshold | 21.3 | Jaccard overlap threshold $\theta_J = 0.4$ for cluster identity across windows. | Split, merge, drift tests |
| **T8** | Review Queue $K, k, N_{\text{review}}$ | 21.8, 21.10 | $K = 5$ entries/window, $k = 3$, $N_{\text{review}} = 6$ windows. | Evaluated for Precision@k on S3 |
| **T9** | Overlap Rates | 20.3 | Pre-registered: Bot normal on Content = 20%, Bot normal on Behavioral = 20%, Bot no Provenance = 15%, Background trip Content = 5%, Background trip Behavioral = 5%, Background share IP/device = 5%. | Pre-registered in config, validated against simulator |

---

## 6. Release Gates (Section 21.10)

- [x] **RG1:** Simulator validation report with pre-registered vs. measured overlap rates ($20.3$).
- [x] **RG2:** Determinism test passes: same seed and config give identical decision log.
- [x] **RG3:** Parameters tuned on tuning seeds (e.g. seed 42), frozen, then evaluated once on held-out seeds (e.g. seed 1337) and held-out generator profile.
- [x] **RG4:** Complete ablation matrix computed from real runs across S2–S5.
- [x] **RG5:** Invariant tests ($I_1$ to $I_8$) pass, including common-cause test, eligible-member test, and mixed-cluster test.
- [x] **RG6:** Claim audit against 19.6 and 19.7 verified.
