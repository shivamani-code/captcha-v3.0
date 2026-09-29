from typing import Optional, Dict, Any, List
from memory_schema import VerifyResponse, SecurityAgentAssessment

class DecisionPolicy:
    """
    Combines baseline ML inference, hard-rule checks, and contextual
    Security Agent assessment into a fully compatible CAPTCHA response.
    """

    @staticmethod
    def build_response(
        prediction: str,
        confidence: float,
        gate: str,
        agent_assessment: Optional[SecurityAgentAssessment] = None,
        memory_status: str = "available",
        retain_status: Optional[str] = None,
    ) -> VerifyResponse:
        # Default baseline values if agent was unavailable
        memory_used = False
        recalled_count = 0
        assessment_str = "unavailable"
        risk_level = "low" if prediction.lower() == "human" else "high"
        hist_context = "Contextual security agent evaluation unavailable; fell back to baseline classifier."
        reason_codes: List[str] = ["BASELINE_CLASSIFIER_ONLY"]
        recommended_action = "allow" if prediction.lower() == "human" else "block"
        mem_relevance = "none"

        if agent_assessment:
            memory_used = agent_assessment.memory_used
            recalled_count = agent_assessment.recalled_memory_count
            assessment_str = agent_assessment.assessment
            risk_level = agent_assessment.risk_level
            hist_context = agent_assessment.historical_context
            reason_codes = agent_assessment.reason_codes
            recommended_action = agent_assessment.recommended_action
            mem_relevance = agent_assessment.memory_relevance

        return VerifyResponse(
            prediction=prediction,
            confidence=round(confidence, 4),
            gate=gate,
            memory_used=memory_used,
            recalled_memory_count=recalled_count,
            agent_assessment=assessment_str,
            risk_level=risk_level,
            memory_status=memory_status,
            historical_context=hist_context,
            reason_codes=reason_codes,
            recommended_action=recommended_action,
            memory_relevance=mem_relevance,
            retain_status=retain_status,
        )

decision_policy = DecisionPolicy()
