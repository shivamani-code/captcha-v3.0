import json
import logging
import math
import re
from typing import Dict, Any, List, Optional, Union

from config import config
from memory_schema import (
    SecurityAgentAssessment,
    SecurityAssessmentOutput,
    SecurityAgentInput,
    RecalledMemoryItem,
)

logger = logging.getLogger("swipecha.security_agent")

class SecurityAgent:
    """
    Security Agent for SwipeCHA.
    Contextual reasoning layer that evaluates:
    1. Current 10-feature behavioral evidence
    2. Current Random Forest prediction & confidence
    3. Deterministic hard-rule gate result
    4. Relevant persistent security memories recalled from Hindsight

    Produces a validated, schema-compliant SecurityAgentAssessment.
    Strictly distinguishes current evidence from historical memory.
    Never invents memories or historical events.
    Gracefully handles zero-memory, malformed model output, and LLM API failures.
    """

    def __init__(self):
        self.provider = config.llm_provider
        self.timeout = config.agent_timeout

    def assess(
        self,
        features: Optional[Union[Dict[str, Any], SecurityAgentInput]] = None,
        ml_prediction: Optional[str] = None,
        ml_confidence: Optional[float] = None,
        hard_rule_triggered: Optional[Union[bool, Dict[str, Any]]] = None,
        recalled_memories: Optional[List[Any]] = None,
        agent_input: Optional[SecurityAgentInput] = None,
        **kwargs,
    ) -> SecurityAgentAssessment:
        """
        Main contextual assessment pipeline.
        Supports both direct arguments and structured SecurityAgentInput.
        Combines current ML evidence with historical memory.
        """
        # 1. Unpack SecurityAgentInput if passed directly or via agent_input/kwargs
        input_obj = agent_input or kwargs.get("input")
        if input_obj is None and isinstance(features, SecurityAgentInput):
            input_obj = features
            features = None
        elif input_obj is None and isinstance(features, dict) and "current_features" in features:
            try:
                input_obj = SecurityAgentInput(**features)
                features = None
            except Exception:
                pass

        if input_obj is not None:
            raw_features = input_obj.current_features
            raw_prediction = input_obj.ml_prediction
            raw_confidence = input_obj.ml_confidence
            hr_val = input_obj.hard_rule_result
            if isinstance(hr_val, dict):
                is_hard_rule = bool(hr_val.get("triggered", False))
            else:
                is_hard_rule = bool(hr_val)
            raw_memories = input_obj.recalled_memories
        else:
            raw_features = features if isinstance(features, dict) else kwargs.get("current_features", {})
            raw_prediction = ml_prediction or kwargs.get("prediction", "Human")
            raw_confidence = ml_confidence if ml_confidence is not None else kwargs.get("confidence", 0.5)
            
            # Normalize hard rule parameter
            hr_candidate = hard_rule_triggered if hard_rule_triggered is not None else kwargs.get("hard_rule_result")
            if isinstance(hr_candidate, dict):
                is_hard_rule = bool(hr_candidate.get("triggered", False))
            else:
                is_hard_rule = bool(hr_candidate)
                
            raw_memories = recalled_memories if recalled_memories is not None else kwargs.get("recalled_memories", [])

        # 2. Normalize and sanitize recalled memories
        normalized_memories: List[RecalledMemoryItem] = []
        if raw_memories:
            for item in raw_memories:
                if isinstance(item, RecalledMemoryItem):
                    normalized_memories.append(item)
                elif isinstance(item, dict):
                    normalized_memories.append(
                        RecalledMemoryItem(
                            id=str(item.get("id", item.get("experience_id", ""))),
                            text=str(item.get("text", item.get("summary", ""))),
                            tags=list(item.get("tags", [])),
                            score=item.get("score") or item.get("relevance_score"),
                            metadata=dict(item.get("metadata", {})),
                            occurred_at=str(item.get("occurred_at", item.get("timestamp", ""))),
                        )
                    )
                else:
                    text_val = getattr(item, "text", None) or getattr(item, "summary", "")
                    id_val = getattr(item, "id", None) or getattr(item, "experience_id", "")
                    normalized_memories.append(
                        RecalledMemoryItem(
                            id=str(id_val),
                            text=str(text_val),
                            tags=list(getattr(item, "tags", []) or []),
                            score=getattr(item, "score", None),
                            metadata=getattr(item, "metadata", {}) or {},
                        )
                    )

        # 3. Sanitize behavioral features
        sanitized_features: Dict[str, float] = {}
        expected_keys = [
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
        for key in expected_keys:
            val = raw_features.get(key)
            try:
                if val is not None and not math.isnan(float(val)) and not math.isinf(float(val)):
                    sanitized_features[key] = float(val)
                else:
                    sanitized_features[key] = 0.0
            except (ValueError, TypeError):
                sanitized_features[key] = 0.0

        # 4. Sanitize confidence
        try:
            sanitized_conf = float(raw_confidence)
            if math.isnan(sanitized_conf) or math.isinf(sanitized_conf):
                sanitized_conf = 0.5
            sanitized_conf = max(0.0, min(1.0, sanitized_conf))
        except (ValueError, TypeError):
            sanitized_conf = 0.5

        # 5. Sanitize prediction string
        sanitized_pred = str(raw_prediction or "Human").strip()
        if sanitized_pred.capitalize() in ("Human", "Bot"):
            sanitized_pred = sanitized_pred.capitalize()
        else:
            sanitized_pred = "Human" if sanitized_conf >= 0.5 else "Bot"

        # 6. Attempt LLM reasoning if configured
        if self.provider in ("openai", "gemini") and config.llm_api_key:
            try:
                assessment = self._assess_with_llm(
                    sanitized_features,
                    sanitized_pred,
                    sanitized_conf,
                    is_hard_rule,
                    normalized_memories,
                )
                if assessment:
                    return assessment
            except Exception as e:
                logger.warning(f"LLM assessment failed ({e}); falling back to expert heuristic reasoning.")

        # 7. Default expert heuristic security evaluation
        return self._assess_with_heuristics(
            sanitized_features,
            sanitized_pred,
            sanitized_conf,
            is_hard_rule,
            normalized_memories,
        )

    def _assess_with_heuristics(
        self,
        features: Dict[str, float],
        ml_prediction: str,
        ml_confidence: float,
        hard_rule_triggered: bool,
        recalled_memories: List[RecalledMemoryItem],
    ) -> SecurityAgentAssessment:
        """
        Deterministic expert security evaluator.
        Provides robust, interpretable contextual assessment without hallucination.
        Distinguishes current evidence from historical memory.
        """
        current_reason_codes: List[str] = []
        historical_reason_codes: List[str] = []
        risk_level: str = "low"
        assessment: str = "human"
        recommended_action: str = "allow"
        historical_context: str = ""
        memory_relevance: str = "none"
        memory_used: bool = False
        recalled_count = len(recalled_memories)

        # --------------------------------------------------
        # 1. Deterministic Hard Rule Gate (First Priority)
        # --------------------------------------------------
        if hard_rule_triggered:
            current_reason_codes.append("HARD_RULE_TRIGGERED")
            risk_level = "high"
            assessment = "bot"
            recommended_action = "block"
            historical_context = "Interaction violated deterministic kinematic boundaries; hard rule triggered."
            return SecurityAgentAssessment(
                assessment=assessment,
                risk_level=risk_level,
                current_ml_prediction="Bot",
                current_ml_confidence=1.0,
                memory_used=False,
                recalled_memory_count=recalled_count,
                historical_context=historical_context,
                reason_codes=current_reason_codes,
                recommended_action=recommended_action,
                memory_relevance="none",
            )

        # --------------------------------------------------
        # 2. Historical Memory Evidence Analysis
        # --------------------------------------------------
        bot_matches = 0
        human_matches = 0

        if recalled_count > 0:
            for mem in recalled_memories:
                text_lower = mem.text.lower()
                tags_lower = [t.lower() for t in mem.tags] if mem.tags else []

                is_bot = (
                    "bot" in text_lower
                    or "final outcome: bot" in text_lower
                    or "high risk" in text_lower
                    or "bot" in tags_lower
                )
                is_human = (
                    "human" in text_lower
                    or "final outcome: human" in text_lower
                    or "low risk" in text_lower
                    or "human" in tags_lower
                )

                if is_bot:
                    bot_matches += 1
                elif is_human:
                    human_matches += 1

            if bot_matches > 0 or human_matches > 0:
                memory_used = True
                memory_relevance = "high" if (bot_matches > 1 or human_matches > 1) else "medium"
            else:
                memory_used = False
                memory_relevance = "low"
        else:
            memory_used = False
            memory_relevance = "none"

        # --------------------------------------------------
        # 3. Current Behavioral Feature Evidence
        # --------------------------------------------------
        speed = features.get("avg_mouse_speed", 0.0)
        entropy = features.get("mouse_path_entropy", 0.5)
        timing_entropy = features.get("timing_entropy", 0.5)
        jitter = features.get("micro_jitter_variance", 10.0)
        duration = features.get("task_completion_time", 1.5)

        is_ml_human = ml_prediction.lower() == "human"

        # Current feature indicators
        if speed > 1000.0 or entropy < 0.08:
            current_reason_codes.append("LOW_ENTROPY_VELOCITY_ANOMALY")
        if jitter > 30.0 and timing_entropy > 0.4 and is_ml_human:
            current_reason_codes.append("NATURAL_HUMAN_TREMOR")
        if timing_entropy > 0.4 and is_ml_human:
            current_reason_codes.append("NATURAL_TIMING_VARIANCE")

        # --------------------------------------------------
        # 4. Contextual Synthesis (ML + Memory)
        # --------------------------------------------------
        if is_ml_human:
            current_reason_codes.append("ML_CONFIRMED_HUMAN")
            assessment = "human"
            risk_level = "low"
            recommended_action = "allow"

            if not memory_used:
                historical_reason_codes.append("ZERO_HISTORY_BASELINE")
                historical_context = "No previous interaction history found in this scope. Establishing baseline."
            else:
                if bot_matches > 0:
                    # Threat pattern recalled from this scope
                    if entropy < 0.20 or speed > 700.0 or jitter < 10.0 or duration < 0.5:
                        # Suspicious correlation: ML indicated Human, but borderline features match prior bot history
                        historical_reason_codes.append("HISTORICAL_BOT_FINGERPRINT_MATCH")
                        historical_reason_codes.append("SUSPICIOUS_HISTORICAL_CORRELATION")
                        risk_level = "medium"
                        assessment = "uncertain"
                        recommended_action = "challenge_again"
                        historical_context = (
                            f"Recalled {bot_matches} prior bot-classified experiences in this scope. "
                            "Current interaction shows borderline kinematic anomalies despite Human ML prediction. "
                            "Secondary verification recommended."
                        )
                    else:
                        historical_reason_codes.append("HISTORICAL_BOT_IN_SCOPE_SUPERVISED")
                        historical_context = (
                            f"Recalled {bot_matches} prior bot interactions in this scope; "
                            "current kinematics demonstrate legitimate human variability. Monitored allow."
                        )
                elif human_matches > 0:
                    historical_reason_codes.append("HISTORICAL_HUMAN_CONSISTENCY")
                    historical_context = (
                        f"Recalled {human_matches} consistent human interactions in this scope. "
                        "Kinematics and timing entropy align with established baseline."
                    )
                else:
                    historical_reason_codes.append("ZERO_RELEVANT_HISTORY")
                    historical_context = "Recalled memories contained no relevant classification evidence."
                    memory_used = False
        else:
            # ML predicted Bot
            current_reason_codes.append("ML_CONFIRMED_BOT")
            assessment = "bot"
            risk_level = "high"
            recommended_action = "block"

            if not memory_used:
                historical_reason_codes.append("FIRST_OBSERVED_ANOMALY")
                historical_reason_codes.append("ZERO_HISTORY_BASELINE")
                historical_context = "First observed automated interaction pattern in this scope. Zero prior history."
            else:
                if bot_matches > 0:
                    historical_reason_codes.append("REPEATED_HIGH_RISK_ATTEMPTS")
                    historical_context = (
                        f"Recalled {bot_matches} prior bot interactions matching robotic velocity/entropy signatures. "
                        "Re-affirms automated threat classification."
                    )
                elif human_matches > 0:
                    historical_reason_codes.append("HISTORICAL_HUMAN_ANOMALOUS_ATTEMPT")
                    risk_level = "medium"
                    assessment = "uncertain"
                    recommended_action = "challenge_again"
                    historical_context = (
                        f"Recalled {human_matches} prior human interactions in this scope, "
                        "but current interaction triggered ML Bot classification. Secondary challenge recommended."
                    )
                else:
                    historical_reason_codes.append("FIRST_OBSERVED_ANOMALY")
                    historical_context = "First observed automated interaction pattern in this scope."

        combined_reason_codes = list(dict.fromkeys(current_reason_codes + historical_reason_codes))

        return SecurityAgentAssessment(
            assessment=assessment,
            risk_level=risk_level,
            current_ml_prediction=ml_prediction,
            current_ml_confidence=round(ml_confidence, 4),
            memory_used=memory_used,
            recalled_memory_count=recalled_count,
            historical_context=historical_context,
            reason_codes=combined_reason_codes,
            recommended_action=recommended_action,
            memory_relevance=memory_relevance,
        )

    def _assess_with_llm(
        self,
        features: Dict[str, float],
        ml_prediction: str,
        ml_confidence: float,
        hard_rule_triggered: bool,
        recalled_memories: List[RecalledMemoryItem],
    ) -> Optional[SecurityAgentAssessment]:
        """
        Structured assessment via OpenAI or other configured LLM.
        Enforces strict schema validation and strips formatting fences.
        """
        system_prompt = (
            "You are the SwipeCHA Security Agent. Assess whether the current CAPTCHA interaction "
            "is from a legitimate Human, an automated Bot, or Uncertain using the provided Random Forest "
            "prediction, behavioral features, hard-rule gate, and recalled historical security memories from Hindsight. "
            "Never invent memories or historical events. If zero memories are provided, set memory_used=false. "
            "Respond ONLY with a valid JSON object with keys: assessment, risk_level, current_ml_prediction, "
            "current_ml_confidence, memory_used, recalled_memory_count, historical_context, reason_codes, "
            "recommended_action, memory_relevance."
        )

        user_content = {
            "current_interaction": {
                "behavioral_features": features,
                "ml_prediction": ml_prediction,
                "ml_confidence": ml_confidence,
                "hard_rule_triggered": hard_rule_triggered,
            },
            "recalled_hindsight_memories": [
                {"id": m.id, "text": m.text, "score": m.score, "tags": m.tags} for m in recalled_memories
            ],
        }

        if self.provider == "openai":
            import openai
            client = openai.OpenAI(api_key=config.llm_api_key, timeout=self.timeout)
            resp = client.chat.completions.create(
                model=config.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_content)},
                ],
                response_format={"type": "json_object"},
            )
            raw_text = resp.choices[0].message.content or ""
            clean_json = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
            clean_json = re.sub(r"\s*```$", "", clean_json, flags=re.MULTILINE).strip()
            parsed = json.loads(clean_json)
            return SecurityAgentAssessment(**parsed)

        return None

security_agent = SecurityAgent()
