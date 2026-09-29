# SwipeCHA + Hindsight Demonstration Guide

## 1. Overview

This guide provides instructions for demonstrating and verifying the multi-turn memory progression of SwipeCHA with persistent Hindsight memory and the Security Agent.

---

## 2. Quick Demonstration (Automated Command-Line Loop)

The automated demonstration executes the full **Steps A through K** multi-interaction cycle:

```powershell
python smartcaptcha/backend/demo_hindsight_loop.py
```

### What Happens During the Automated Loop:
1. **Service Auto-Detection:** Automatically detects if a Hindsight service is responding on `127.0.0.1:8888`. If not, it automatically launches the local mock Hindsight server in a background daemon thread.
2. **Step A (Clean Scope):** Generates an isolated memory bank (`demo-session-<uuid>`) and verifies it is completely empty.
3. **Steps B & C (First Human Interaction):** Evaluates a legitimate human swipe.
   - ML: Predicts `Human` (confidence > 98%).
   - Recall: Returns 0 memories.
   - Security Agent: Evaluates baseline, sets `memory_used = False`, records `ZERO_HISTORY_BASELINE`.
4. **Step D (Retain First Experience):** Distills and persists the first human verification experience into Hindsight.
5. **Step E (Additional Experiences):** Performs and retains a second human interaction and a robotic automated attempt.
6. **Steps F -> I (Contextual Recall & Assessment):** Performs a subsequent human interaction in the same bank.
   - Recall: Semantically retrieves the previous experiences from the bank.
   - Security Agent: Receives live telemetry + recalled experiences.
   - Contextual Output: Sets `memory_used = True`, records `HISTORICAL_HUMAN_CONSISTENCY` (or `HISTORICAL_BOT_IN_SCOPE_SUPERVISED`), cites historical context, and outputs `allow`.
7. **Step J (Retain New Experience):** Persists the new interaction.
8. **Step K (Process Restart Persistence):** Terminates the existing client service, instantiates a fresh client instance, executes recall, and verifies that the retained experiences persist across process lifecycles.

---

## 3. Interactive Browser Demonstration

### Step 1: Start the Backend Service
From the repository root:
```powershell
python -m uvicorn smartcaptcha.backend.app:app --port 8000
```

### Step 2: Open the Frontend
Open `index.html` in any modern web browser, or serve it via a local static file server:
```powershell
python -m http.server 3000
```
Navigate to `http://127.0.0.1:3000`.

### Step 3: Observe the Developer View
Expand the **Security Observability & Hindsight Memory (Developer View)** panel below the slider to observe real-time security signals:
- **Hindsight Status:** Displays connection health (`connected`, `available`, `disabled`).
- **ML Prediction & Confidence:** Authoritative output from the Random Forest classifier.
- **Decision Gate:** Indicates whether the decision was formed by deterministic hard rules (`hard_rule`) or statistical inference (`ml`).
- **Security Agent:** Contextual verdict (`human`, `bot`, `uncertain`).
- **Risk Level:** Risk categorization (`low`, `medium`, `high`).
- **Memory Used:** `Yes` if prior experiences were recalled and informed reasoning; `No` if fresh baseline.
- **Recalled Experiences:** Count of retrieved historical interactions.
- **Recommended Action:** Action policy (`allow`, `challenge_again`, `block`).
- **Contextual Reasoning:** Detailed textual rationale explaining the combination of live kinetic telemetry and historical memory.

### Step 4: Before vs. After Memory Progression
1. **Turn 1 (Fresh Session):** Complete the slider normally. Observe `Memory Used: No`, `Recalled: 0`, Reason code: `ZERO_HISTORY_BASELINE`.
2. **Turn 2 (Follow-up Swipe):** Click Reset and complete the slider again. Observe `Memory Used: Yes`, `Recalled: 1+`, Reason code: `HISTORICAL_HUMAN_CONSISTENCY`.
3. **Turn 3 (Borderline Evasion Scrutiny):** When a borderline or suspicious velocity curve occurs in a scope with prior bot history, the Security Agent escalates risk to `medium`, sets assessment to `uncertain`, and triggers `recommended_action: "challenge_again"`, prompting the widget for secondary verification.
