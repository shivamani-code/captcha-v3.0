import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field

class BehaviorSummary(BaseModel):
    avg_mouse_speed: float
    mouse_path_entropy: float
    click_delay: float
    task_completion_time: float
    idle_time: float
    micro_jitter_variance: float
    acceleration_curve: float
    curvature_variance: float
    overshoot_correction_ratio: float
    timing_entropy: float

class SecurityExperience(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source: str = "SwipeCHA"
    bank_id: str
    behavior_summary: Dict[str, float]
    ml_prediction: str
    ml_confidence: float
    gate: str
    hard_rule_result: Literal["pass", "triggered"]
    agent_assessment: str
    risk_level: str
    final_outcome: str
    risk_indicators: List[str] = Field(default_factory=list)
    reason_context: str
    tags: List[str] = Field(default_factory=list)

    def to_natural_language(self) -> str:
        """
        Formats distilled experience into structured natural language for Hindsight retention.
        Ensures Hindsight's fact extraction extracts semantic facts cleanly.
        """
        b = self.behavior_summary
        return (
            f"SwipeCHA security verification attempt recorded at {self.timestamp}. "
            f"Final outcome: {self.final_outcome}. "
            f"ML classifier: {self.ml_prediction} (confidence: {self.ml_confidence:.4f}, gate: {self.gate}). "
            f"Hard rule status: {self.hard_rule_result}. "
            f"Security agent assessment: {self.agent_assessment} (risk level: {self.risk_level}). "
            f"Key telemetry: avg_speed={b.get('avg_mouse_speed', 0.0):.1f} px/s, "
            f"path_entropy={b.get('mouse_path_entropy', 0.0):.3f}, "
            f"completion_time={b.get('task_completion_time', 0.0):.2f}s, "
            f"jitter_variance={b.get('micro_jitter_variance', 0.0):.2f}, "
            f"timing_entropy={b.get('timing_entropy', 0.0):.3f}, "
            f"overshoot_ratio={b.get('overshoot_correction_ratio', 0.0):.3f}. "
            f"Risk indicators: {', '.join(self.risk_indicators) if self.risk_indicators else 'none'}. "
            f"Context: {self.reason_context}"
        )

class RecalledMemoryItem(BaseModel):
    id: str
    text: str
    tags: List[str] = Field(default_factory=list)
    score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    occurred_at: Optional[str] = None

class SecurityAgentAssessment(BaseModel):
    assessment: Literal["human", "bot", "uncertain"]
    risk_level: Literal["low", "medium", "high"]
    current_ml_prediction: str
    current_ml_confidence: float
    memory_used: bool
    recalled_memory_count: int
    historical_context: str
    reason_codes: List[str]
    recommended_action: Literal["allow", "challenge_again", "block", "review"]
    memory_relevance: Literal["high", "medium", "low", "none"]

# Contract alias matching docs/INTEGRATION_CONTRACT.md
SecurityAssessmentOutput = SecurityAgentAssessment
RecalledExperience = RecalledMemoryItem

class SecurityAgentInput(BaseModel):
    current_features: Dict[str, float]
    ml_prediction: str
    ml_confidence: float
    hard_rule_result: Dict[str, Any] = Field(default_factory=lambda: {"triggered": False, "gate": "pass"})
    recalled_memories: List[RecalledMemoryItem] = Field(default_factory=list)
    session_context: Optional[Dict[str, Any]] = None

class VerifyResponse(BaseModel):
    # Core compatible fields
    prediction: str
    confidence: float
    gate: str
    
    # Additive Hindsight & Security Agent fields
    memory_used: bool = False
    recalled_memory_count: int = 0
    agent_assessment: str = "unavailable"
    risk_level: str = "unknown"
    memory_status: Literal["available", "unavailable", "error", "disabled", "skipped"] = "unavailable"
    historical_context: Optional[str] = None
    reason_codes: List[str] = Field(default_factory=list)
    recommended_action: str = "allow"
    memory_relevance: str = "none"
    retain_status: Optional[str] = None
