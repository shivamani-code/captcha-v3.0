import math
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from security_agent import SecurityAgent, security_agent
from memory_schema import (
    SecurityAgentAssessment,
    SecurityAssessmentOutput,
    SecurityAgentInput,
    RecalledMemoryItem,
)

@pytest.fixture
def human_features():
    return {
        "avg_mouse_speed": 340.5,
        "mouse_path_entropy": 0.65,
        "click_delay": 1.2,
        "task_completion_time": 1.8,
        "idle_time": 0.2,
        "micro_jitter_variance": 45.0,
        "acceleration_curve": 1200.0,
        "curvature_variance": 0.04,
        "overshoot_correction_ratio": 0.08,
        "timing_entropy": 0.75,
    }

@pytest.fixture
def bot_features():
    return {
        "avg_mouse_speed": 2200.0,
        "mouse_path_entropy": 0.02,
        "click_delay": 0.05,
        "task_completion_time": 0.15,
        "idle_time": 0.01,
        "micro_jitter_variance": 0.05,
        "acceleration_curve": 20.0,
        "curvature_variance": 0.0001,
        "overshoot_correction_ratio": 0.001,
        "timing_entropy": 0.03,
    }

@pytest.fixture
def borderline_features():
    return {
        "avg_mouse_speed": 720.0,
        "mouse_path_entropy": 0.14,
        "click_delay": 0.18,
        "task_completion_time": 0.45,
        "idle_time": 0.05,
        "micro_jitter_variance": 8.0,
        "acceleration_curve": 600.0,
        "curvature_variance": 0.005,
        "overshoot_correction_ratio": 0.02,
        "timing_entropy": 0.22,
    }

# =========================================================================
# 1. Zero-Memory Operation (Mandatory Contract Test)
# =========================================================================

def test_zero_memory_human_baseline(human_features):
    """
    When zero memories are recalled, the agent must:
    1. Set memory_used=False
    2. Set recalled_memory_count=0
    3. Set memory_relevance='none'
    4. State in historical_context that baseline is being established
    5. Reason strictly on current behavioral evidence without hallucinating history
    """
    result = security_agent.assess(
        features=human_features,
        ml_prediction="Human",
        ml_confidence=0.985,
        hard_rule_triggered=False,
        recalled_memories=[],
    )

    assert isinstance(result, SecurityAgentAssessment)
    assert result.assessment == "human"
    assert result.risk_level == "low"
    assert result.current_ml_prediction == "Human"
    assert result.current_ml_confidence == 0.985
    assert result.memory_used is False
    assert result.recalled_memory_count == 0
    assert result.memory_relevance == "none"
    assert result.recommended_action == "allow"
    assert "establishing baseline" in result.historical_context.lower() or "no previous" in result.historical_context.lower()
    assert "ZERO_HISTORY_BASELINE" in result.reason_codes
    assert "ML_CONFIRMED_HUMAN" in result.reason_codes

def test_zero_memory_bot_baseline(bot_features):
    """
    When zero memories are recalled for a bot attempt:
    Agent confirms Bot classification from ML without inventing prior history.
    """
    result = security_agent.assess(
        features=bot_features,
        ml_prediction="Bot",
        ml_confidence=0.992,
        hard_rule_triggered=False,
        recalled_memories=[],
    )

    assert isinstance(result, SecurityAgentAssessment)
    assert result.assessment == "bot"
    assert result.risk_level == "high"
    assert result.memory_used is False
    assert result.recalled_memory_count == 0
    assert result.memory_relevance == "none"
    assert result.recommended_action == "block"
    assert "ZERO_HISTORY_BASELINE" in result.reason_codes
    assert "ML_CONFIRMED_BOT" in result.reason_codes

# =========================================================================
# 2. Hard Rule Override Test
# =========================================================================

def test_hard_rule_override(human_features):
    """
    Hard rule trigger must immediately produce a Bot assessment and block action,
    taking precedence over ML and historical memories.
    """
    mem = RecalledMemoryItem(id="m1", text="Past interaction was human.", score=0.9)
    result = security_agent.assess(
        features=human_features,
        ml_prediction="Human",
        ml_confidence=0.99,
        hard_rule_triggered=True,
        recalled_memories=[mem],
    )

    assert result.assessment == "bot"
    assert result.risk_level == "high"
    assert result.recommended_action == "block"
    assert result.current_ml_confidence == 1.0
    assert result.memory_used is False
    assert "HARD_RULE_TRIGGERED" in result.reason_codes

# =========================================================================
# 3. Recalled Memory Actually Reaches and Influences Agent
# =========================================================================

def test_recalled_memory_reaches_agent_human_reinforcement(human_features):
    """
    Recalled previous human experiences confirm baseline consistency:
    1. memory_used must be True
    2. recalled_memory_count must match inputs
    3. memory_relevance must be high
    4. reason_codes must cite historical human consistency
    """
    memories = [
        RecalledMemoryItem(
            id="mem-1",
            text="SwipeCHA security verification attempt. Final outcome: Human. Low risk. ML: Human (confidence 0.98).",
            score=0.95,
            tags=["swipecha", "human"],
        ),
        RecalledMemoryItem(
            id="mem-2",
            text="SwipeCHA verification. Final outcome: Human. Natural tremor detected. Low risk.",
            score=0.91,
            tags=["swipecha", "human"],
        ),
    ]

    result = security_agent.assess(
        features=human_features,
        ml_prediction="Human",
        ml_confidence=0.97,
        hard_rule_triggered=False,
        recalled_memories=memories,
    )

    assert result.memory_used is True
    assert result.recalled_memory_count == 2
    assert result.memory_relevance == "high"
    assert result.assessment == "human"
    assert result.risk_level == "low"
    assert result.recommended_action == "allow"
    assert "HISTORICAL_HUMAN_CONSISTENCY" in result.reason_codes
    assert "Recalled 2 consistent human interactions" in result.historical_context

def test_recalled_memory_reaches_agent_repeated_bot_attacks(bot_features):
    """
    Recalled previous bot experiences reinforce threat classification for repeated bot attempts.
    """
    memories = [
        RecalledMemoryItem(
            id="mem-bot-1",
            text="SwipeCHA verification. Final outcome: Bot. High risk. ML: Bot (confidence 0.99). Robotic velocity.",
            score=0.98,
            tags=["swipecha", "bot"],
        ),
    ]

    result = security_agent.assess(
        features=bot_features,
        ml_prediction="Bot",
        ml_confidence=0.99,
        hard_rule_triggered=False,
        recalled_memories=memories,
    )

    assert result.memory_used is True
    assert result.recalled_memory_count == 1
    assert result.assessment == "bot"
    assert result.risk_level == "high"
    assert result.recommended_action == "block"
    assert "REPEATED_HIGH_RISK_ATTEMPTS" in result.reason_codes
    assert "Recalled 1 prior bot interactions" in result.historical_context

def test_recalled_memory_contextualizes_borderline_evasion(borderline_features):
    """
    Crucial contextual reasoning test:
    Current ML classifier predicted 'Human' (perhaps borderline),
    BUT Hindsight recalled prior bot interactions in this scope.
    The agent detects kinematic anomalies (low entropy, high speed),
    elevates risk from 'low' to 'medium', sets assessment='uncertain',
    and recommends 'challenge_again'.
    """
    memories = [
        RecalledMemoryItem(
            id="mem-bot-prev",
            text="SwipeCHA verification. Final outcome: Bot. High risk. Automated script pattern.",
            score=0.92,
            tags=["swipecha", "bot"],
        ),
    ]

    result = security_agent.assess(
        features=borderline_features,
        ml_prediction="Human",
        ml_confidence=0.62,
        hard_rule_triggered=False,
        recalled_memories=memories,
    )

    assert result.memory_used is True
    assert result.assessment == "uncertain"
    assert result.risk_level == "medium"
    assert result.recommended_action == "challenge_again"
    assert "HISTORICAL_BOT_FINGERPRINT_MATCH" in result.reason_codes
    assert "SUSPICIOUS_HISTORICAL_CORRELATION" in result.reason_codes
    assert "prior bot-classified experiences" in result.historical_context

# =========================================================================
# 4. Never Invent History / Memory (Strict Truthfulness)
# =========================================================================

def test_never_invent_historical_events(human_features):
    """
    When zero memories are provided, the agent must NEVER invent bot attacks,
    human sessions, or previous encounters.
    """
    result = security_agent.assess(
        features=human_features,
        ml_prediction="Human",
        ml_confidence=0.95,
        hard_rule_triggered=False,
        recalled_memories=[],
    )

    assert result.memory_used is False
    assert result.recalled_memory_count == 0
    assert "HISTORICAL_BOT_FINGERPRINT_MATCH" not in result.reason_codes
    assert "HISTORICAL_HUMAN_CONSISTENCY" not in result.reason_codes
    assert "REPEATED_HIGH_RISK_ATTEMPTS" not in result.reason_codes

# =========================================================================
# 5. Handling Malformed Model Output & LLM Failures
# =========================================================================

def test_llm_markdown_code_fence_cleaning(human_features):
    """
    Verify that if LLM returns JSON enclosed in ```json ... ``` fences,
    the agent parses it cleanly without failing.
    """
    agent = SecurityAgent()
    agent.provider = "openai"

    mock_llm_response = MagicMock()
    mock_llm_response.choices = [
        MagicMock(message=MagicMock(content="""```json
{
  "assessment": "human",
  "risk_level": "low",
  "current_ml_prediction": "Human",
  "current_ml_confidence": 0.98,
  "memory_used": false,
  "recalled_memory_count": 0,
  "historical_context": "Clean baseline interaction.",
  "reason_codes": ["ML_HUMAN_HIGH_CONFIDENCE"],
  "recommended_action": "allow",
  "memory_relevance": "none"
}
```"""))
    ]

    with patch("config.config.llm_api_key", "sk-mock-test-key"):
        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_llm_response
            mock_openai_cls.return_value = mock_client

            result = agent.assess(
                features=human_features,
                ml_prediction="Human",
                ml_confidence=0.98,
                hard_rule_triggered=False,
                recalled_memories=[],
            )

            assert isinstance(result, SecurityAgentAssessment)
            assert result.assessment == "human"
            assert result.risk_level == "low"
            assert result.reason_codes == ["ML_HUMAN_HIGH_CONFIDENCE"]

def test_malformed_llm_output_fallback(human_features):
    """
    Verify that if the LLM returns invalid JSON or garbage text,
    the agent catches the error and safely falls back to heuristic reasoning.
    """
    agent = SecurityAgent()
    agent.provider = "openai"

    mock_llm_response = MagicMock()
    mock_llm_response.choices = [
        MagicMock(message=MagicMock(content="This is not valid JSON at all! <b>Error 500</b>"))
    ]

    with patch("config.config.llm_api_key", "sk-mock-test-key"):
        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_llm_response
            mock_openai_cls.return_value = mock_client

            result = agent.assess(
                features=human_features,
                ml_prediction="Human",
                ml_confidence=0.98,
                hard_rule_triggered=False,
                recalled_memories=[],
            )

            # Fallback must produce a valid schema-compliant heuristic assessment
            assert isinstance(result, SecurityAgentAssessment)
            assert result.assessment == "human"
            assert result.risk_level == "low"
            assert result.memory_used is False

def test_llm_api_network_failure_fallback(human_features):
    """
    Verify that if the LLM raises a connection error or timeout,
    the agent catches it and safely falls back to heuristic reasoning.
    """
    agent = SecurityAgent()
    agent.provider = "openai"

    with patch("config.config.llm_api_key", "sk-mock-test-key"):
        with patch("openai.OpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = TimeoutError("Connection to OpenAI timed out")
            mock_openai_cls.return_value = mock_client

            result = agent.assess(
                features=human_features,
                ml_prediction="Human",
                ml_confidence=0.98,
                hard_rule_triggered=False,
                recalled_memories=[],
            )

            assert isinstance(result, SecurityAgentAssessment)
            assert result.assessment == "human"
            assert result.risk_level == "low"
            assert "ML_CONFIRMED_HUMAN" in result.reason_codes

# =========================================================================
# 6. Structured Input Polymorphism (SecurityAgentInput Contract)
# =========================================================================

def test_security_agent_input_model(human_features):
    """
    Verify that agent accepts the formal SecurityAgentInput Pydantic model
    as specified in docs/INTEGRATION_CONTRACT.md.
    """
    agent_input = SecurityAgentInput(
        current_features=human_features,
        ml_prediction="Human",
        ml_confidence=0.965,
        hard_rule_result={"triggered": False, "gate": "pass"},
        recalled_memories=[],
    )

    result = security_agent.assess(agent_input)

    assert isinstance(result, SecurityAgentAssessment)
    assert result.assessment == "human"
    assert result.current_ml_prediction == "Human"
    assert result.current_ml_confidence == 0.965
    assert result.memory_used is False

def test_security_agent_dict_input(human_features):
    """
    Verify that agent accepts a dictionary matching SecurityAgentInput.
    """
    input_dict = {
        "current_features": human_features,
        "ml_prediction": "Human",
        "ml_confidence": 0.95,
        "hard_rule_result": {"triggered": False, "gate": "pass"},
        "recalled_memories": [],
    }

    result = security_agent.assess(input_dict)

    assert isinstance(result, SecurityAgentAssessment)
    assert result.assessment == "human"
    assert result.memory_used is False

# =========================================================================
# 7. Resilient Edge Case & Boundary Handling
# =========================================================================

def test_edge_case_nan_and_missing_values():
    """
    Verify that NaN confidence, missing feature keys, and None memories
    do not cause uncaught exceptions.
    """
    incomplete_features = {
        "avg_mouse_speed": float("nan"),
        "mouse_path_entropy": 0.5,
    }

    result = security_agent.assess(
        features=incomplete_features,
        ml_prediction=None,
        ml_confidence=float("nan"),
        hard_rule_triggered=None,
        recalled_memories=None,
    )

    assert isinstance(result, SecurityAgentAssessment)
    assert result.current_ml_confidence == 0.5
    assert result.memory_used is False
    assert result.recalled_memory_count == 0

def test_schema_conformance_with_integration_contract(human_features):
    """
    Verify that every output field is present and strictly matches
    the SecurityAssessmentOutput contract.
    """
    result = security_agent.assess(
        features=human_features,
        ml_prediction="Human",
        ml_confidence=0.99,
        hard_rule_triggered=False,
        recalled_memories=[],
    )

    result_dict = result.model_dump()
    expected_keys = {
        "assessment",
        "risk_level",
        "current_ml_prediction",
        "current_ml_confidence",
        "memory_used",
        "recalled_memory_count",
        "historical_context",
        "reason_codes",
        "recommended_action",
        "memory_relevance",
    }
    assert expected_keys.issubset(set(result_dict.keys()))
    assert result.assessment in ("human", "bot", "uncertain")
    assert result.risk_level in ("low", "medium", "high")
    assert result.recommended_action in ("allow", "challenge_again", "block", "review")
    assert result.memory_relevance in ("high", "medium", "low", "none")
    assert isinstance(result.reason_codes, list)
    assert isinstance(result.historical_context, str)
    assert isinstance(result.memory_used, bool)
