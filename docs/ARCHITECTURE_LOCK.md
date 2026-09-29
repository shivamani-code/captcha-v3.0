# ARCHITECTURE LOCK

## Status: LOCKED
**Lock Date:** 2026-09-28  
**Lock Authority:** PHASE 1 — FOUNDATION / ARCHITECTURE LEAD  
**Approval Required For Modification:** Final Integration Lead / Release Lead

---

## 1. Target System Architecture

The following architectural flow is strictly locked. No phase may re-order, bypass, or replace components without explicit authorization.

```
USER INTERACTION (Browser)
      ↓
Pointer & Gesture Dynamics (smartcaptcha.js)
      ↓
10-Feature Behavioral Extraction
      ↓
Client-Side Heuristic Pre-Filter
      ↓
POST /verify (FastAPI: smartcaptcha/backend/app.py)
      ↓
Challenge Token Validation & Single-Use Consumption
      ↓
Deterministic Hard Bot Rule First Gate
      │
      ├── [Triggered] ──────────────────────────────────────────┐
      │                                                         │
      └── [Passes]                                              │
            ↓                                                   │
      Existing Random Forest Classifier                         │
      (smartcaptcha/backend/captcha_model.pkl)                  │
            ↓                                                   │
      Current ML Prediction & Confidence                        │
            ↓                                                   │
      Hindsight RECALL                                          │
      (Query: Current behavioral & risk context)                │
            ↓                                                   │
      Security Agent                                            │
      (Contextual reasoning over:                               │
       Current Features + RF Output + Hard Gate + Memory)       │
            ↓                                                   │
      Structured Contextual Security Assessment                 │
            ↓                                                   │
      Final Compatible Decision Filter                          │
      ("Human" / "Bot" + confidence + gate) ◄───────────────────┘
            ↓
      Hindsight RETAIN
      (Async / safe persistence of distilled security experience)
            ↓
      Client Response (Standard format + Observability metadata)
            ↓
      Future Interactions (Persistently recall stored experience)
```

---

## 2. Core Architectural Roles (Non-Negotiable)

### 2.1 Random Forest Classifier (Current Behavioral Intelligence)
- **Role:** Primary ML behavioral classifier for the current interaction vector.
- **Artifact:** `smartcaptcha/backend/captcha_model.pkl` (200 estimators, max depth 10, 10 features).
- **Responsibility:** Evaluates the 10-feature behavioral vector and generates:
  - Binary classification: `1` (Human) or `0` (Bot).
  - Confidence score: `max(predict_proba)`.
- **STRICT PROHIBITION:** **DO NOT replace the Random Forest with an LLM.** The LLM is NOT a replacement classifier. The Random Forest is the authoritative statistical model trained on mouse dynamics.

### 2.2 Hindsight Memory (Persistent Experience Memory)
- **Role:** Long-term episodic and contextual memory of prior security interactions.
- **Responsibility:**
  - **RECALL:** Given the current behavioral context and interaction characteristics, retrieves relevant past security encounters from the scoped memory bank.
  - **RETAIN:** After a verification decision is formed, distills the interaction into a compact security experience and stores it durably in Hindsight.
- **Requirements:**
  - Genuine connection via official Hindsight API (`hindsight-client`).
  - Memory **must persist** across requests and process restarts.
  - Recalled memory **must actually reach and influence** the Security Agent.
  - No mock JSON, no in-memory dictionaries pretending to be Hindsight.

### 2.3 Security Agent (Contextual Reasoning Layer)
- **Role:** Higher-order contextual evaluator.
- **Inputs:**
  1. Current 10 behavioral feature values.
  2. Random Forest prediction and confidence score.
  3. Hard-rule gate evaluation status.
  4. Recalled Hindsight security experiences.
  5. Security policy guidelines.
- **Output:** Validated, schema-enforced structured assessment (`SecurityAssessmentOutput`).
- **Responsibility:** Identifies behavioral anomalies, recognizes repeated attack patterns from historical memory, verifies ML classification consistency, and produces structured risk rationale.
- **STRICT RULE:** The agent must never invent historical events or fabricate memories. When zero relevant memories are recalled, the agent must clearly state `memory_used = False` and reason solely on current evidence.

### 2.4 Final Compatible Decision Layer
- **Role:** Translates the combined intelligence into a response compatible with the existing SwipeCHA frontend and client integrations.
- **Compatibility Rule:** The `/verify` endpoint must preserve standard response keys (`prediction`, `confidence`, `gate`). Extended security metadata (`agent_assessment`, `memory_context`) can be included for developer observability and demo panels without breaking existing clients.

---

## 3. Memory Retention & Privacy Policy

1. **Selective Distillation (NO Raw Coordinate Streams):**
   - Under no circumstances should raw mouse coordinate arrays `[{x, y, t}, ...]` be stored in persistent long-term Hindsight memory.
   - Retain only **distilled security experiences** containing summary metrics, ML outputs, agent risk assessments, and decision reason codes.

2. **Bank Scoping & Isolation:**
   - Every Hindsight interaction must operate within an explicit `bank_id`.
   - Different tenants, users, or test suites must be partitioned to prevent cross-contamination or behavioral leakage.
   - A dedicated prefix/namespace convention must be enforced (e.g., `swipecha_prod_{tenant_id}`, `swipecha_test_{session_id}`).

3. **No Credential or PII Retention:**
   - No passwords, session secrets, API tokens, IP addresses, or personal identifiable information may be retained in Hindsight.
   - Challenge IDs are ephemeral single-use tokens and must never be stored as durable identifiers in memory banks.

---

## 4. Graceful Degradation & Fail-Safe Architecture

The security system must maintain 100% operational uptime for the baseline CAPTCHA even during third-party AI or network outages.

| Component Failure | System Behavior | Fallback Path |
|---|---|---|
| **Hindsight Service Unavailable (Timeout / Connection Error)** | Normal CAPTCHA verification continues unaffected. | `memory_used = False`. Security Agent proceeds with zero memories, or falls back to direct Random Forest output. |
| **Security Agent Unavailable (LLM API Failure / Timeout)** | Normal CAPTCHA verification continues unaffected. | Final decision falls back directly to Random Forest prediction and confidence (`gate: "ml"`). |
| **Hindsight Retain Failure** | Current verification request succeeds with 200 OK. | Retain error is logged as a non-blocking warning. User interaction is not failed. |
| **Random Forest Model Missing** | Fallback to safe conservative default. | Returns `{"prediction": "Human", "confidence": 0.5, "gate": "fallback"}`. |
| **Invalid / Expired Challenge Token** | Deterministic rejection before ML/AI layers. | Returns HTTP 400 or HTTP 403. Zero AI/ML computation consumed. |

---

## 5. Authoritative vs Legacy Codebase Mapping

| Repository Path | Status | Role & Ownership |
|---|---|---|
| `smartcaptcha/backend/app.py` | **AUTHORITATIVE BACKEND** | Primary FastAPI service, ML inference, hard rules, challenge tokens. Insertion point for Hindsight & Security Agent. |
| `smartcaptcha/backend/captcha_model.pkl` | **AUTHORITATIVE MODEL** | 10-feature scikit-learn Random Forest model. DO NOT OVERWRITE. |
| `smartcaptcha.js` (Root) | **AUTHORITATIVE FRONTEND** | 788-line production frontend script with full 10-feature extraction, canvas handle, and anti-tamper measures. |
| `index.html` (Root) | **AUTHORITATIVE DEMO UI** | Main user-facing demonstration page. |
| `smartcaptcha/ml/train_model.py` | **AUTHORITATIVE ML PIPELINE** | Training script, hyperparameter definitions, evaluation pipeline. |
| `reports/stress_test.py` | **AUTHORITATIVE TEST** | Baseline automated stress and security test suite. |
| `backend/app.py` (Root) | **LEGACY MOCK** | 28-line mock prototype. DO NOT USE FOR INTEGRATION. |
| `smartcaptcha/frontend/smartcaptcha.js` | **LEGACY FRONTEND** | Older 126-line prototype. Superseded by root `smartcaptcha.js`. |

---

## 6. Prohibited Anti-Patterns

1. **NO "CAPTCHA → LLM" Replacement:** Under no circumstances should the Random Forest classifier be swapped out for an LLM prompt.
2. **NO Fake Memory:** In-memory dictionaries, local JSON files, or simulated sleep delays claiming to be Hindsight are strictly prohibited.
3. **NO Cosmetic Memory:** Recalled memories must actually be passed into the Security Agent prompt/reasoning context and influence its evaluation.
4. **NO Invented History:** If Hindsight returns no relevant memories, the agent must not invent or assume prior attacks.
5. **NO Hardcoded Credentials:** All API keys, endpoints, and bank tokens must be loaded exclusively via environment variables.
