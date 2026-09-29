# SwipeCHA — Hindsight Memory Demonstration Script (Steps A -> K)

This script documents the step-by-step reproducible demonstration proving that Hindsight persistent experience memory genuinely connects to SwipeCHA, influences the Security Agent's contextual assessment, and persists across backend restarts.

---

## 1. Quick Automated Execution

To run the complete automated sequence:
```powershell
python smartcaptcha/backend/demo_hindsight_loop.py
```

---

## 2. Detailed Step-by-Step Walkthrough

### Step A: Initialize an Empty Memory Scope
- Establish a unique, isolated Hindsight bank ID: `demo-session-<uuid>`.
- Query the bank to confirm initial memory count is `0`.
- **System State:** Clean memory slate.

### Step B & C: First Human Interaction (Zero-Memory Baseline)
- Submit a natural human swipe interaction (`speed: 320 px/s`, `entropy: 0.68`, `timing_entropy: 0.82`).
- **ML Classifier Output:** `Human`, `Confidence: 98.50%`, `Gate: ml`.
- **Hindsight Recall:** `0` memories retrieved.
- **Security Agent Assessment:**
  - `assessment: HUMAN`
  - `risk_level: LOW`
  - `memory_used: false`
  - `recalled_memory_count: 0`
  - `reason_codes: ["ZERO_HISTORY_BASELINE", "ML_CONFIRMED_HUMAN", "NATURAL_TIMING_VARIANCE"]`
  - `historical_context: "No previous interaction history found in this scope. Establishing baseline."`

### Step D: Retain the First Experience
- Retain distilled natural language experience to Hindsight:
  > *"SwipeCHA security verification attempt recorded at 2026-09-28T17:31:56Z. Final outcome: Human. ML classifier: Human (confidence: 0.9850, gate: ml)..."*
- **Retain Status:** `retained` (`success: True`).

### Step E: Perform and Retain Subsequent Interactions
- **Interaction #2 (Human):** Smooth swipe with human tremor retained (`tags: ["swipecha", "security", "human"]`).
- **Interaction #3 (Bot):** Automated robotic swipe (`speed: 2800 px/s`, `entropy: 0.015`) triggering hard rule and retained (`tags: ["swipecha", "security", "bot"]`).

### Step F: Later Interaction with Related Behavioral Pattern
- Submit another human swipe within the same scope.

### Step G: Hindsight Semantic Recall
- Recall query automatically constructed using live kinematic telemetry:
  `"SwipeCHA security experience for interaction: speed=330.0px/s, path_entropy=0.660, completion_time=1.80s, jitter_variance=52.00, timing_entropy=0.800, ML=Human, hard_rule=pass."`
- **Result:** Retrieves `3` relevant previous experiences from Hindsight with high similarity scores.

### Step H: Security Agent Receives Recalled Memory
- The Security Agent receives:
  1. Live 10 behavioral features
  2. Live Random Forest prediction (`Human`, 98.8%)
  3. Hard-rule gate outcome (`pass`)
  4. The 3 retrieved Hindsight memory items

### Step I: Contextual Assessment Informed by Memory
- **Security Agent Assessment:**
  - `assessment: HUMAN`
  - `risk_level: LOW`
  - `memory_used: true`
  - `recalled_memory_count: 3`
  - `memory_relevance: high`
  - `historical_context: "Recalled 1 prior bot interactions in this scope; current kinematics demonstrate legitimate human variability. Monitored allow."`
  - `reason_codes: ["ML_CONFIRMED_HUMAN", "HISTORICAL_HUMAN_CONSISTENCY", "NATURAL_TIMING_VARIANCE"]`
  - `recommended_action: allow`

### Step J: Retain the New Experience
- The updated contextual assessment and telemetry are retained into Hindsight (`retain_status: retained`).

### Step K: Simulate Restart and Verify Persistence
- Terminate the active backend / client session.
- Instantiate a new `HindsightMemoryService` instance.
- Recall from `demo-session-<uuid>`.
- **Result:** All `4` accumulated security experiences are successfully recalled from persistent storage.

---

## 3. Web UI Demonstration

1. Start the backend:
   ```powershell
   python -m uvicorn app:app --port 8000 --host 127.0.0.1
   ```
2. Open `index.html` in your browser.
3. Observe the **Security Observability & Hindsight Memory (Developer View)** panel.
4. Complete a swipe to see:
   - Live ML Prediction and Confidence
   - Decision Gate (`ml` or `hard_rule`)
   - Hindsight Connection Status (`connected`)
   - Recalled Experiences Count
   - Memory Used (`Yes` / `No`)
   - Security Agent Verdict and Risk Level (`LOW` / `HIGH`)
   - Retain Status (`retained`)
   - Contextual Reasoning narrative
