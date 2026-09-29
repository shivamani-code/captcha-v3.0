import pytest
from memory_schema import SecurityExperience
from hindsight_memory import HindsightMemoryService

def test_bank_isolation(sample_human_features, sample_bot_features):
    service = HindsightMemoryService(base_url="http://127.0.0.1:8888")

    bank_alpha = "tenant-session-alpha"
    bank_beta = "tenant-session-beta"

    # Retain human experience in alpha
    exp_alpha = SecurityExperience(
        bank_id=bank_alpha,
        behavior_summary=sample_human_features,
        ml_prediction="Human",
        ml_confidence=0.99,
        gate="ml",
        hard_rule_result="pass",
        agent_assessment="human",
        risk_level="low",
        final_outcome="Human",
        reason_context="Alpha session distinct fingerprint human",
        tags=["swipecha", "security", "human"],
    )
    s_alpha, _ = service.retain(exp_alpha, bank_id=bank_alpha)
    assert s_alpha is True

    # Retain bot experience in beta
    exp_beta = SecurityExperience(
        bank_id=bank_beta,
        behavior_summary=sample_bot_features,
        ml_prediction="Bot",
        ml_confidence=1.0,
        gate="hard_rule",
        hard_rule_result="triggered",
        agent_assessment="bot",
        risk_level="high",
        final_outcome="Bot",
        reason_context="Beta session distinct fingerprint robotic automated",
        tags=["swipecha", "security", "bot"],
    )
    s_beta, _ = service.retain(exp_beta, bank_id=bank_beta)
    assert s_beta is True

    # Recall in alpha should retrieve alpha's experience only
    recalled_alpha, _ = service.recall("human alpha", bank_id=bank_alpha)
    assert len(recalled_alpha) >= 1
    for mem in recalled_alpha:
        assert "Alpha session" in mem.text
        assert "Beta session" not in mem.text

    # Recall in beta should retrieve beta's experience only
    recalled_beta, _ = service.recall("bot beta", bank_id=bank_beta)
    assert len(recalled_beta) >= 1
    for mem in recalled_beta:
        assert "Beta session" in mem.text
        assert "Alpha session" not in mem.text

    # Querying a brand-new empty bank should yield zero results
    recalled_gamma, _ = service.recall("human bot", bank_id="tenant-session-gamma")
    assert len(recalled_gamma) == 0
