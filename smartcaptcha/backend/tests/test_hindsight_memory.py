import pytest
from config import config
from memory_schema import SecurityExperience
from hindsight_memory import HindsightMemoryService

def test_hindsight_health_check(sample_human_features):
    service = HindsightMemoryService(base_url="http://127.0.0.1:8888")
    healthy, status = service.check_health()
    assert healthy is True
    assert "connected" in status

def test_hindsight_retain_and_recall(sample_human_features):
    service = HindsightMemoryService(base_url="http://127.0.0.1:8888", bank_id="test-bank-retain")
    experience = SecurityExperience(
        bank_id="test-bank-retain",
        behavior_summary=sample_human_features,
        ml_prediction="Human",
        ml_confidence=0.98,
        gate="ml",
        hard_rule_result="pass",
        agent_assessment="human",
        risk_level="low",
        final_outcome="Human",
        risk_indicators=["ML_CONFIRMED_HUMAN"],
        reason_context="Natural human timing entropy observed.",
        tags=["swipecha", "security", "human"],
    )

    success, retain_status = service.retain(experience)
    assert success is True
    assert retain_status == "retained"

    query = service.build_recall_query(sample_human_features, "Human", "pass")
    assert "speed" in query
    assert "path_entropy" in query

    memories, mem_status = service.recall(query, bank_id="test-bank-retain")
    assert mem_status == "available"
    assert len(memories) >= 1
    assert "Human" in memories[0].text
    assert memories[0].score is not None

def test_hindsight_offline_fallback():
    # Intentionally point to an unused port to simulate an offline server
    offline_service = HindsightMemoryService(base_url="http://127.0.0.1:59998", timeout=0.3)
    healthy, status = offline_service.check_health()
    assert healthy is False
    assert status == "unavailable"

    memories, mem_status = offline_service.recall("query about human bot")
    assert memories == []
    assert mem_status in ("unavailable", "error")

    experience = SecurityExperience(
        bank_id="test-offline",
        behavior_summary={},
        ml_prediction="Human",
        ml_confidence=0.5,
        gate="fallback",
        hard_rule_result="pass",
        agent_assessment="human",
        risk_level="low",
        final_outcome="Human",
        reason_context="Fallback test",
    )
    success, ret_status = offline_service.retain(experience)
    assert success is False
    assert ret_status in ("failed", "unavailable", "timeout")

def test_hindsight_memory_disabled(sample_human_features, monkeypatch):
    monkeypatch.setattr(config, "enable_memory", False)
    service = HindsightMemoryService(base_url="http://127.0.0.1:8888")

    memories, mem_status = service.recall("query")
    assert memories == []
    assert mem_status == "disabled"

    experience = SecurityExperience(
        bank_id="test-disabled",
        behavior_summary=sample_human_features,
        ml_prediction="Human",
        ml_confidence=0.9,
        gate="ml",
        hard_rule_result="pass",
        agent_assessment="human",
        risk_level="low",
        final_outcome="Human",
        reason_context="Disabled test",
    )
    success, ret_status = service.retain(experience)
    assert success is False
    assert ret_status == "skipped"
