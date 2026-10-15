# BreachX 2026 / HYDRA: Authoritative 3-Minute Demonstration Script
**Specification Reference:** Section 21.16 (Authoritative Demo Cut v1.7)  
**Target Duration:** 3 minutes (180 seconds)  

---

## Act 1: The Quiet Network & Baseline Health (0:00 – 0:15)
- **Action:** Open dashboard on **Scenario S1: Baseline (Clean / Decoys Only)**.
- **Narrative:**
  > *"Welcome to BreachX / HYDRA. We are demonstrating autonomous coordinated bot network detection. Before demonstrating attacks, we begin with a quiet network containing background users and three legitimate decoy groups: a high-engagement music fan community, high-volume automated news feeds, and a campus NAT network.*
  > *Notice that all 177 accounts remain at State 0: Observe. Zero user-impacting actions are taken. All results presented today are measured on our deterministic synthetic benchmark, where raw identifiers are converted to keyed HMAC-SHA256 hashes."*
- **Key Visual:** Status bar shows 0 throttled, 0 challenged, 0 restricted accounts. Green "Engine Online" indicator.

---

## Act 2: Coordinated Bot Farm Attack Launches (0:15 – 0:45)
- **Action:** Select **Scenario S2: Naive Bot Farm**. Click **Play** or step through windows to Window 3.
- **Narrative:**
  > *"In Window 2, a 40-account bot farm launches a coordinated astroturfing campaign targeting corporate brands with templated messages and synchronized posting bursts.*
  > *On our force-directed graph, accounts sharing hardware devices, co-timed posting, and semantic similarity rapidly coalesce into a tight cluster. Notice how the state halos on the bot nodes shift from cyan (Observe) to amber (Throttle) as risk accumulates across consecutive windows."*
- **Key Visual:** Distinct bot cluster forms in the center; nodes glow amber as Louvain clustering groups them.

---

## Act 3: The Centerpiece — The Decoy Explanation Moment (0:45 – 1:30)
- **Action:** In the cluster selector, click the **Fan Community Decoy** cluster (`fan_comm`).
- **Narrative:**
  > *"This is the centerpiece of our design: look-alike legitimate communities must never be punished. Here is our legitimate Fan Community. Notice that because they share hashtags and lyrics around a concert tour, their Content evidence score is elevated.*
  > *Under conventional single-signal detectors, this fan group would be falsely banned. But look at our Non-Compensatory Evidence Gate: it displays 'Gate REFUSED (Behavior-Only): Active groups lack required Provenance evidence. Automated user-impacting action blocked.'*
  > *Right below, our exact Counterfactual Engine proves why: 'Without Provenance evidence, the cluster strictly fails Invariant I1 and remains at State 0 (Observe).' Even if fans look coordinated, without shared operator hardware or burst signup, automation cannot touch them."*
- **Key Visual:** Red/Amber "Gate REFUSED" banner on evidence card, showing Provenance ✗, Content ✓. Counterfactual card explaining exact log-odds difference.

---

## Act 4: Graduated Response Ladder & Audit Log (1:30 – 2:00)
- **Action:** Select the **Bot Farm** cluster. Step forward to Window 6. Click the **Audit Log & Chain** tab.
- **Narrative:**
  > *"Returning to the bot farm, it satisfies our multi-group requirement with Provenance, Behavioral, and Content evidence all active. Notice our graduated ladder in action: Invariant I2 prohibits jumping straight to a ban. The farm progresses strictly one step at a time: Observe to Throttle, Throttle to Verification Challenge, and Challenge to Temporary Restriction.*
  > *Notice our Member-Level Eligibility rule in action: in this 40-account farm, only accounts with direct hardware links are restricted. Unlinked bots remain at Observe with a review flag.*
  > *Every single transition is appended to our SHA-256 cryptographic hash chain, recording the exact rule that fired."*
- **Key Visual:** State progression timeline. Audit table showing each transition with its SHA-256 record hash.

---

## Act 5: Attacker Adaptation & Cost of Evasion (2:00 – 2:45)
- **Action:** Switch to the **Evaluation & Arms-Race** tab. Show **Cost-of-Evasion** chart.
- **Narrative:**
  > *"What happens when the attacker adapts? In our multi-round evaluation, we tested a scripted attacker schedule. In Round 2, the attacker paraphrases content; our semantic similarity holds. In Round 3, they jitter posting times; our provenance signals hold.*
  > *In Round 4, the attacker eliminates shared hardware by purchasing 40 distinct virtual devices and proxy IPs. Look at our Cost-of-Evasion curve: while the attacker escaped automated restriction, their campaign throughput collapsed by 65%, and their device infrastructure costs increased tenfold.*
  > *Furthermore, as shown in our Review Queue panel, zero-provenance campaigns do not disappear—they are prioritized by Coordination Score C_c and routed to human analysts."*
- **Key Visual:** Cost-of-evasion downward curve (Throughput retained vs. round). Review Queue table with Precision@k metrics.

---

## Act 6: Cryptographic Verification & Tamper Demo (2:45 – 3:00)
- **Action:** Switch to **Audit Log & Chain** tab. Click **"Verify Chain"** (shows green checkmark). Then click **"Tamper Demo (M14b)"**.
- **Narrative:**
  > *"To guarantee accountability (Invariant I7), our audit log is tamper-evident. When we click 'Verify Chain', the entire cryptographic log passes. Now, let's simulate an adversary or malicious insider tampering with an old record. We click 'Tamper Demo'—and instantly, the verification algorithm flags corruption at the exact modified index.*
  > *In conclusion: BreachX / HYDRA enforces that no single signal triggers restriction, protects legitimate decoys, and guarantees reversibility and mathematical explainability."*
- **Key Visual:** Instant red alert: `[CORRUPTION AT #14] Hash mismatch at record index 14`.
