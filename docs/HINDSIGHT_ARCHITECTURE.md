# SwipeCHA + Hindsight: Persistent Experience Memory Architecture

## 1. Executive Summary

SwipeCHA (SwipeCAPTCHA) was originally designed as a behavioral CAPTCHA distinguishing humans from automated bots by evaluating kinematic swipe telemetry using an offline-trained Random Forest classifier. While effective at single-interaction classification, it possessed no memory of prior interactions, no capability to detect distributed or slow-rate automated attacks across requests, and no contextual reasoning layer.

With **Step 5: Full Integration**, SwipeCHA is upgraded with **Hindsight persistent experience memory** and an autonomous **Security Agent**. The original Random Forest classifier is fully preserved as the foundational behavioral signal. Hindsight acts as the long-term, cross-request memory layer that retains distilled interaction experiences and recalls relevant historical context. The Security Agent evaluates the combination of live ML evidence and recalled historical memory to produce a contextual security assessment.

---

## 2. Target Verification Architecture

```
User Gesture
    │
    ▼
SwipeCHA UI (Pointer Events Capture)
    │
    ▼
10 Behavioral Features Extraction
    (avg_mouse_speed, mouse_path_entropy, click_delay, task_completion_time,
     idle_time, micro_jitter_variance, acceleration_curve, curvature_variance,
     overshoot_correction_ratio, timing_entropy)
    │
    ▼
Client-Side Heuristic Checks
    │
    ▼
POST /verify (FastAPI Verifier Service)
    │
    ├─► 1. Challenge Token Validation (Single-use, 300s expiry)
    │
    ├─► 2. Server Hard-Rule First Gate (Deterministic kinematic violation check)
    │
    ├─► 3. Random Forest Classifier (200 trees, 10 features -> Prediction & Confidence)
    │
    ├─► 4. Hindsight Semantic RECALL
    │        └── Retrieves relevant prior security experiences for the current pattern
    │
    ├─► 5. Security Agent Assessment
    │        ├── Input A: Live 10 behavioral features
    │        ├── Input B: ML prediction & confidence
    │        ├── Input C: Hard-rule gate outcome
    │        └── Input D: Recalled prior security experiences
    │        └── Output: Structured assessment (risk_level, reason_codes, action)
    │
    ├─► 6. Decision Policy
    │        └── Synthesizes final backward-compatible CAPTCHA response
    │
    ├─► 7. Hindsight RETAIN
    │        └── Distills new interaction into long-term security experience
    │
    └─► 8. Client Response & Future Experience Availability
```

---

## 3. Core Architectural Principles

1. **Preserve Baseline Integrity:** The Random Forest classifier, client heuristics, 10-feature schema, challenge lifecycle, and hard-rule checks remain 100% active and uncompromised.
2. **Experience Distillation over Raw Dumps:** Durable memory stores compact, semantic security experiences (ML outcomes, key behavioral metrics, agent verdicts, reason codes), never raw pointer streams or sensitive tokens.
3. **Semantic Querying:** Recall queries are constructed dynamically using the interaction's kinetic characteristics (`speed`, `entropy`, `jitter`, `timing_entropy`, `ml_prediction`), preventing indiscriminate memory dumping.
4. **Scoped Bank Isolation:** Memories are partitioned using Hindsight's `bank_id` scoping mechanism, preventing cross-tenant or unintended cross-session memory leakage.
5. **Zero-Crash Graceful Fallbacks:** If the Hindsight service or LLM provider becomes unavailable or times out, verification continues uninterrupted using baseline Random Forest classification.

---

## 4. Hindsight Memory Service (`hindsight_memory.py`)

The memory service interfaces directly with the official `hindsight-client` Python SDK (`v0.10.1`).

### Retention Contract
```python
experience = SecurityExperience(
    bank_id="tenant-session-id",
    behavior_summary={...},
    ml_prediction="Human",
    ml_confidence=0.985,
    gate="ml",
    hard_rule_result="pass",
    agent_assessment="human",
    risk_level="low",
    final_outcome="Human",
    risk_indicators=["ML_CONFIRMED_HUMAN"],
    reason_context="Natural human timing entropy observed.",
    tags=["swipecha", "security", "human"]
)
success, status = hindsight_service.retain(experience)
```

Natural language distillation:
> *"SwipeCHA security verification attempt recorded at 2026-09-28T17:31:56Z. Final outcome: Human. ML classifier: Human (confidence: 0.9850, gate: ml). Hard rule status: pass. Security agent assessment: human (risk level: low). Key telemetry: avg_speed=320.0 px/s, path_entropy=0.680, completion_time=1.70s, jitter_variance=50.00, timing_entropy=0.820. Risk indicators: ML_CONFIRMED_HUMAN."*

### Recall Contract
```python
query = hindsight_service.build_recall_query(features, ml_prediction, hard_rule_status)
memories, status = hindsight_service.recall(query, bank_id=bank_id)
```
- Query focuses on behavioral signatures rather than generic keywords.
- Returns normalized `List[RecalledMemoryItem]` containing text, relevance score, tags, and timestamps.

---

## 5. Security Agent (`security_agent.py`)

The Security Agent does not replace the ML model; it contextualizes it.

### Structured Output Schema
```json
{
  "assessment": "human | bot | uncertain",
  "risk_level": "low | medium | high",
  "current_ml_prediction": "Human",
  "current_ml_confidence": 0.985,
  "memory_used": true,
  "recalled_memory_count": 2,
  "historical_context": "Recalled 2 consistent human interactions in this scope. Kinematics and timing entropy align with established baseline.",
  "reason_codes": [
    "ML_CONFIRMED_HUMAN",
    "HISTORICAL_HUMAN_CONSISTENCY",
    "NATURAL_TIMING_VARIANCE"
  ],
  "recommended_action": "allow | challenge_again | block | review",
  "memory_relevance": "high | medium | low | none"
}
```

### Contextual Reasoning Modes
- **Zero-History Baseline:** First interaction in a fresh bank. Sets `memory_used: false`, assigns `ZERO_HISTORY_BASELINE`, evaluates purely on live evidence.
- **Human Consistency Reinforcement:** Prior human experiences in scope reinforce confidence and mark `HISTORICAL_HUMAN_CONSISTENCY`.
- **Evasion Detection & Risk Escalation:** If an interaction produces a borderline ML prediction but historical memories reveal prior bot attempts in the same scope, the agent escalates risk to `medium`, assessment to `uncertain`, and action to `challenge_again` (`HISTORICAL_BOT_FINGERPRINT_MATCH`).
- **Deterministic Hard-Rule Lockdown:** Obvious kinematic violations bypass memory and immediately trigger high-risk blocking.

---

## 6. Verification Response Contract

The `/verify` endpoint maintains 100% backwards compatibility by preserving all existing fields (`prediction`, `confidence`, `gate`) while providing additive observability attributes:

```json
{
  "prediction": "Human",
  "confidence": 0.985,
  "gate": "ml",
  "memory_used": true,
  "recalled_memory_count": 2,
  "agent_assessment": "human",
  "risk_level": "low",
  "memory_status": "available",
  "historical_context": "Recalled 2 consistent human interactions in this scope.",
  "reason_codes": [
    "ML_CONFIRMED_HUMAN",
    "HISTORICAL_HUMAN_CONSISTENCY"
  ],
  "recommended_action": "allow",
  "memory_relevance": "high",
  "retain_status": "retained"
}
```

---

## 7. Failure and Resilience Modes

| Failure Condition | System Response | CAPTCHA Outcome |
| :--- | :--- | :--- |
| **Hindsight Offline / Timeout** | `memory_status = "unavailable"`, `memory_used = false`. Fall back to live ML inference. | Verification succeeds normally. |
| **Hindsight Recall Error** | Handled safely, returns empty memory list, `memory_status = "error"`. | Verification completes with baseline ML. |
| **Security Agent / LLM Error** | Logs warning, falls back to deterministic heuristic reasoning. | Baseline decision preserved. |
| **Hindsight Retain Failure** | Logs warning safely, reports `retain_status = "failed"`. | Verification outcome is NOT invalidated. |
| **Invalid / Expired Challenge** | Rejected before ML or memory execution (`400` or `403`). | Hard security perimeter preserved. |
