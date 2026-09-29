# INTEGRATION CONTRACT

## Status: APPROVED
**Author:** PHASE 1 — FOUNDATION / ARCHITECTURE LEAD  
**Effective Date:** 2026-09-28  
**Applicability:** Phases 2, 3, 4, 5, 6

---

## 1. Overview

This document specifies the exact technical contracts, data models, function signatures, and communication protocols between the four core subsystems of the enhanced SwipeCHA architecture:

1. **Random Forest Behavioral Classifier** (`smartcaptcha/backend/captcha_model.pkl`)
2. **Hindsight Memory Module** (`smartcaptcha/backend/hindsight_memory.py`)
3. **Security Agent Module** (`smartcaptcha/backend/security_agent.py`)
4. **FastAPI Verification Pipeline** (`smartcaptcha/backend/app.py`)

All phase leads must adhere strictly to these schemas.

---

## 2. Behavioral Feature Vector Contract

The system processes an exact sequence of 10 behavioral features extracted from the pointer/swipe trajectory. The order, keys, and types must remain strictly consistent between frontend telemetry, ML training, and inference.

### 2.1 Feature Definitions

| Index | Feature Key | Type | Unit / Scale | Description |
|---|---|---|---|---|
| 0 | `avg_mouse_speed` | `float` | px / ms | Mean Euclidean velocity across all trajectory segments. |
| 1 | `mouse_path_entropy` | `float` | [0.0, 1.0] | Normalized Shannon entropy of movement direction angles (8-bin histogram). |
| 2 | `click_delay` | `float` | seconds | Time delta between mousedown and initial movement, or mouseup click delay. |
| 3 | `task_completion_time` | `float` | seconds | Total swipe duration from drag start to drag release. |
| 4 | `idle_time` | `float` | seconds | Cumulative time where pointer velocity remained near zero (<120ms intervals). |
| 5 | `micro_jitter_variance` | `float` | px² | High-frequency orthogonal positional variance (sub-conscious human tremor). |
| 6 | `acceleration_curve` | `float` | px / s² | Rate of change of velocity; measures acceleration variability along the curve. |
| 7 | `curvature_variance` | `float` | rad² | Variance of trajectory curvature angles along the path. |
| 8 | `overshoot_correction_ratio`| `float` | [0.0, 1.0] | Ratio of backward corrective movement to total trajectory distance. |
| 9 | `timing_entropy` | `float` | [0.0, 1.0] | Temporal entropy of inter-event timestamp intervals. |

### 2.2 Vector Ordering
```python
FEATURE_COLUMNS = [
    "avg_mouse_speed",
    "mouse_path_entropy",
    "click_delay",
    "task_completion_time",
    "idle_time",
    "micro_jitter_variance",
    "acceleration_curve",
    "curvature_variance",
    "overshoot_correction_ratio",
    "timing_entropy",
]
```

---

## 3. Hard-Rule Gate Contract

### 3.1 Hard Rule Trigger Condition
Catches naive scripted bots with unnatural speed, zero jitter, perfectly straight paths, and artificial timing regularity:

```python
is_naive_bot = (
    speed > 2.2 and
    entropy < 0.08 and
    delay < 0.2 and
    duration < 0.8 and
    jitter < 0.2 and
    timing_entropy < 0.10
)
```

### 3.2 Output Contract
If triggered:
```json
{
  "prediction": "Bot",
  "confidence": 1.0,
  "gate": "hard_rule"
}
```

---

## 4. Random Forest Classifier Contract

### 4.1 Interface Specification
```python
class RandomForestClassifierContract:
    def predict(self, X: List[List[float]]) -> np.ndarray:
        """
        Takes a 2D array of shape (1, 10) containing FEATURE_COLUMNS in order.
        Returns array([0]) for Bot, array([1]) for Human.
        """
        ...

    def predict_proba(self, X: List[List[float]]) -> np.ndarray:
        """
        Returns array([[P(bot), P(human)]]) of shape (1, 2).
        Confidence is calculated as float(max(proba[0])).
        """
        ...
```

### 4.2 Output Structure
```python
{
    "prediction": "Human" if int(pred) == 1 else "Bot",
    "confidence": round(float(max(proba)), 4),
    "gate": "ml"
}
```

---

## 5. Hindsight Memory Contract (Phase 2 Owner)

### 5.1 Memory Module Interface
Located at: `smartcaptcha/backend/hindsight_memory.py`

```python
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class DistilledSecurityExperience(BaseModel):
    experience_id: str = Field(description="Unique UUID for this experience")
    timestamp: float = Field(description="Epoch timestamp in seconds")
    interaction_type: str = Field(default="swipe_captcha")
    bank_id: str = Field(description="Target isolated memory bank identifier")
    behavioral_summary: Dict[str, float] = Field(description="Key behavioral features: speed, entropy, jitter, duration")
    ml_result: Dict[str, Any] = Field(description="{'prediction': 'Human'|'Bot', 'confidence': float, 'gate': str}")
    hard_rule_triggered: bool = Field(default=False)
    agent_assessment: Optional[str] = Field(default=None)
    risk_level: Optional[str] = Field(default=None)
    final_outcome: str = Field(description="'allow' | 'block' | 'challenge_again'")
    reason_codes: List[str] = Field(default_factory=list)
    risk_indicators: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list, description="Tags for retrieval: e.g. ['high_speed', 'jitter_anomaly', 'bot']")

class RecalledExperience(BaseModel):
    experience_id: str
    timestamp: float
    summary: str
    relevance_score: float
    behavioral_summary: Optional[Dict[str, Any]] = None
    ml_result: Optional[Dict[str, Any]] = None
    risk_level: Optional[str] = None
    outcome: Optional[str] = None
    raw_document: Optional[str] = None

class HindsightMemoryService:
    def recall_security_experiences(
        self,
        current_context: Dict[str, Any],
        bank_id: str,
        limit: int = 5
    ) -> List[RecalledExperience]:
        """
        Retrieves top relevant past security encounters from the specified bank_id.
        Query must focus on behavioral similarity, repeated anomaly patterns, and prior outcomes.
        Returns empty list [] if no relevant experiences exist or on failure.
        """
        ...

    def retain_security_experience(
        self,
        experience: DistilledSecurityExperience,
        bank_id: str
    ) -> bool:
        """
        Stores a distilled security experience into Hindsight.
        Returns True on successful retention, False on failure.
        MUST NOT raise uncaught exceptions to caller.
        """
        ...
```

### 5.2 Recall Query Contract
Recall queries must be specific and grounded in security attributes:
```python
def build_recall_query(context: Dict[str, Any]) -> str:
    return (
        f"Find previous SwipeCHA security experiences with behavioral pattern: "
        f"avg_speed={context.get('avg_mouse_speed')}, "
        f"path_entropy={context.get('mouse_path_entropy')}, "
        f"jitter={context.get('micro_jitter_variance')}, "
        f"ML prediction={context.get('ml_prediction')} (confidence={context.get('ml_confidence')}). "
        f"Identify prior bot or human classifications with similar velocity or entropy anomalies."
    )
```

---

## 6. Security Agent Contract (Phase 3 Owner)

### 6.1 Agent Input Specification
Located at: `smartcaptcha/backend/security_agent.py`

```python
class SecurityAgentInput(BaseModel):
    current_features: Dict[str, float]
    ml_prediction: str              # "Human" | "Bot"
    ml_confidence: float            # 0.0 to 1.0
    hard_rule_result: Dict[str, Any]# {"triggered": bool, "gate": str}
    recalled_memories: List[RecalledExperience]
    session_context: Optional[Dict[str, Any]] = None
```

### 6.2 Agent Output Specification (`SecurityAssessmentOutput`)
```python
from typing import Literal

class SecurityAssessmentOutput(BaseModel):
    assessment: Literal["human", "bot", "uncertain"] = Field(
        description="Contextual classification"
    )
    risk_level: Literal["low", "medium", "high"] = Field(
        description="Assessed security risk"
    )
    current_ml_prediction: str = Field(
        description="Echo of current Random Forest prediction"
    )
    current_ml_confidence: float = Field(
        description="Echo of current Random Forest confidence"
    )
    memory_used: bool = Field(
        description="True if relevant historical memories were recalled and influenced analysis"
    )
    recalled_memory_count: int = Field(
        description="Number of relevant memories provided to the agent"
    )
    historical_context: str = Field(
        description="Summary of historical patterns or 'No relevant previous interactions found.'"
    )
    reason_codes: List[str] = Field(
        description="Standardized rationale codes, e.g. ['ML_HUMAN_HIGH_CONF', 'SIMILAR_BOT_PATTERN_RECALLED']"
    )
    recommended_action: Literal["allow", "challenge_again", "block", "review"] = Field(
        description="Recommended policy action"
    )
    memory_relevance: Literal["high", "medium", "low", "none"] = Field(
        description="Degree of relevance of recalled memories to the current interaction"
    )
```

---

## 7. Verification Endpoint (`/verify`) Contract (Phase 4 Owner)

### 7.1 Request Schema
```json
{
  "challenge_id": "string (hex UUID, required)",
  "avg_mouse_speed": "float (required)",
  "mouse_path_entropy": "float (required)",
  "click_delay": "float (required)",
  "task_completion_time": "float (required)",
  "idle_time": "float (required)",
  "micro_jitter_variance": "float (required)",
  "acceleration_curve": "float (required)",
  "curvature_variance": "float (required)",
  "overshoot_correction_ratio": "float (required)",
  "timing_entropy": "float (required)",
  "bank_id": "string (optional, for tenant/demo memory partitioning)"
}
```

### 7.2 Baseline Backward-Compatible Response Schema
Every successful response MUST contain these 3 top-level keys so existing frontend/SDK consumers never break:
```json
{
  "prediction": "Human",
  "confidence": 0.9842,
  "gate": "ml"
}
```

### 7.3 Extended Observability Response Schema
For developer panels, demo views, and security dashboards, extended metadata is attached under safe keys:
```json
{
  "prediction": "Human",
  "confidence": 0.9842,
  "gate": "ml",
  "security_assessment": {
    "assessment": "human",
    "risk_level": "low",
    "recommended_action": "allow",
    "memory_used": true,
    "recalled_memory_count": 2,
    "memory_relevance": "medium",
    "historical_context": "Previous interactions from this device pattern demonstrated consistent natural human tremor.",
    "reason_codes": [
      "ML_HUMAN_HIGH_CONFIDENCE",
      "CONSISTENT_WITH_HISTORICAL_HUMAN"
    ]
  },
  "memory_status": {
    "hindsight_available": true,
    "bank_id": "swipecha_default",
    "recalled_count": 2,
    "retained": true
  }
}
```

### 7.4 HTTP Status Codes
- `200 OK`: Valid challenge and completed verification assessment.
- `400 Bad Request`: Missing `challenge_id`.
- `403 Forbidden`: Invalid, already consumed (replay), or expired (>300s) `challenge_id`.
- `422 Unprocessable Entity`: Malformed feature values (non-numeric, missing required fields).

---

## 8. Failure & Fallback Decision Matrix

| Failure Event | Hard Gate Action | RF Action | Hindsight Action | Agent Action | Response Gate | Returned Prediction |
|---|---|---|---|---|---|---|
| **Normal Operation (No Prior Memory)** | Passes | Evaluates | Recalls 0 items | Reasons on ML only (`memory_used=False`) | `"ml"` / `"agent"` | Matches ML / Agent consensus |
| **Normal Operation (With Memory)** | Passes | Evaluates | Recalls N items | Reasons on ML + Memory (`memory_used=True`) | `"ml"` / `"agent"` | Matches contextual assessment |
| **Hard Bot Rule Triggered** | Triggers | Skipped | Skipped | Skipped | `"hard_rule"` | `"Bot"` (conf 1.0) |
| **Hindsight Network Failure** | Passes | Evaluates | Returns `[]` | Evaluates with zero memories | `"ml"` | Matches RF |
| **LLM / Agent Service Timeout** | Passes | Evaluates | Recalls | Times out → fallback | `"ml"` | Matches RF directly |
| **Hindsight Retain Fails** | Passes | Evaluates | Recalls | Assesses | `"ml"` | Normal 200 OK returned |
| **Missing Model File** | Passes | Skipped | Skipped | Skipped | `"fallback"` | `"Human"` (conf 0.5) |
