import os
import pytest
from memory_schema import SecurityExperience
from hindsight_memory import HindsightMemoryService
from mock_hindsight_server import STORAGE_FILE

def test_memory_persists_across_instances(sample_human_features):
    bank_id = "persistent-test-bank"
    service_instance_1 = HindsightMemoryService(base_url="http://127.0.0.1:8888", bank_id=bank_id)

    exp = SecurityExperience(
        bank_id=bank_id,
        behavior_summary=sample_human_features,
        ml_prediction="Human",
        ml_confidence=0.98,
        gate="ml",
        hard_rule_result="pass",
        agent_assessment="human",
        risk_level="low",
        final_outcome="Human",
        reason_context="Experience intended to persist across service instances",
        tags=["swipecha", "security", "human"],
    )

    success, _ = service_instance_1.retain(exp)
    assert success is True
    assert os.path.exists(STORAGE_FILE)

    # Simulate server/process restart by deleting service instance and recreating a brand-new instance
    del service_instance_1

    service_instance_2 = HindsightMemoryService(base_url="http://127.0.0.1:8888", bank_id=bank_id)
    recalled, status = service_instance_2.recall("persist across service instances", bank_id=bank_id)
    assert status == "available"
    assert len(recalled) >= 1
    assert "persist across service instances" in recalled[0].text
