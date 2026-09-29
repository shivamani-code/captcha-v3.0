# SwipeCHA Hindsight Memory Policy

## 1. Overview & Objectives

SwipeCHA enhances standard behavioral CAPTCHA classification with persistent historical security memory powered by Hindsight. The memory policy governs what information is retained, how it is scoped, how privacy and security boundaries are enforced, and how experiences are recalled.

---

## 2. Retention Policy: What is Stored vs. Never Stored

### 2.1 Strictly Prohibited Data (Never Retained)
- **Raw Pointer Coordinates:** Raw coordinate streams `[{x, y, t}, ...]` or pixel drag paths are **never** stored in Hindsight memory. Storing raw sensor streams creates excessive storage bloat, violates behavioral privacy principles, and provides poor semantic retrieval value.
- **Personally Identifiable Information (PII):** User emails, usernames, real names, phone numbers, or account credentials must never be included in memory experiences.
- **Network / Transport Identifiers:** IP addresses, browser cookies, and full user-agent strings are excluded from persistent memory.
- **Ephemeral Secrets:** Single-use `challenge_id` tokens are cryptographic nonces meant for one-time verification. They must never be persisted as long-term memory identifiers.

### 2.2 Authorized Distilled Security Experiences (Stored)
Durable memory stores compact, semantic **security experiences** captured as structured natural language and indexed attributes:
1. **Timestamp:** ISO 8601 UTC timestamp of the verification attempt.
2. **Kinetic Summary Telemetry:**
   - Average mouse velocity (`avg_mouse_speed`)
   - Path direction entropy (`mouse_path_entropy`)
   - Interaction timing entropy (`timing_entropy`)
   - Micro-jitter variance (`micro_jitter_variance`)
   - Task completion duration (`task_completion_time`)
   - Overshoot corrective movement ratio (`overshoot_correction_ratio`)
3. **Machine Learning Evidence:**
   - Random Forest prediction (`Human` or `Bot`)
   - Classification confidence score (0.0 to 1.0)
   - Decision gate (`ml`, `hard_rule`, `fallback`)
4. **Hard-Rule Status:** `pass` or `triggered`.
5. **Security Agent Assessment:**
   - Assessment verdict (`human`, `bot`, `uncertain`)
   - Assessed risk level (`low`, `medium`, `high`)
   - Standardized reason codes (e.g. `ML_CONFIRMED_HUMAN`, `HISTORICAL_BOT_FINGERPRINT_MATCH`)
   - Recommended action (`allow`, `challenge_again`, `block`, `review`)
6. **Semantic Tags:** e.g., `["swipecha", "security", "human"]` or `["swipecha", "security", "bot"]`.

---

## 3. Scoping & Multi-Tenant Bank Isolation

1. **Explicit Bank Scoping:**
   - Every read (`recall`) and write (`retain`) operation must specify an explicit `bank_id`.
   - By default, requests use `swipecha-security-bank`.
   - Applications may supply a tenant-specific, application-specific, or session-scoped `bank_id` in the verification payload:
     ```json
     {
       "challenge_id": "...",
       "bank_id": "tenant_acme_corp",
       ...
     }
     ```
2. **Cross-Tenant Isolation:**
   - Memories retained within `bank_A` are completely invisible to queries executed against `bank_B`.
   - Multi-tenant isolation is tested and verified by automated integration tests.

---

## 4. Recall Policy & Query Construction

1. **Kinetic Signature Querying:**
   - Queries are constructed dynamically based on the current interaction's kinetic characteristics (`speed`, `entropy`, `jitter`, `timing_entropy`, `ml_prediction`).
   - Querying focuses on matching anomalous or consistent behavioral patterns rather than broad keyword dumps.
2. **Truthfulness & Zero-Memory Behavior:**
   - When recall returns 0 relevant experiences for a fresh bank, the Security Agent strictly sets `memory_used = False` and outputs the reason code `ZERO_HISTORY_BASELINE`.
   - The Security Agent is prohibited from hallucinating past encounters or inventing historical data.

---

## 5. Resilience & Outage Protection

1. **Non-Blocking Operation:**
   - If the Hindsight memory service times out or becomes unreachable, the baseline Random Forest classifier continues to function normally.
   - An in-memory circuit breaker trips after repeated consecutive failures, fast-bypassing memory calls in 0ms to eliminate outage latency.
2. **Non-Destructive Failures:**
   - Failures during retention log a safe warning; they never cause a valid human verification attempt to fail with an error.
