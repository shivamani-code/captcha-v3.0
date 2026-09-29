import time
import pytest
from app import challenges
from hindsight_memory import hindsight_service
from security_agent import security_agent

def get_challenge_token(client):
    res = client.get("/challenge")
    assert res.status_code == 200
    return res.json()["challenge_id"]

# 1. Normal Human Interaction
def test_normal_human_interaction(client, sample_human_features):
    cid = get_challenge_token(client)
    payload = dict(sample_human_features)
    payload["challenge_id"] = cid
    payload["bank_id"] = "test-flow-human"

    res = client.post("/verify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["prediction"] == "Human"
    assert data["gate"] in ("ml", "fallback")
    assert data["confidence"] > 0.5
    assert data["agent_assessment"] == "human"
    assert data["risk_level"] == "low"
    assert data["memory_status"] == "available"
    assert data["retain_status"] == "retained"

# 2. Bot-like Interaction
def test_bot_like_interaction(client, sample_bot_features):
    cid = get_challenge_token(client)
    payload = dict(sample_bot_features)
    payload["challenge_id"] = cid
    payload["bank_id"] = "test-flow-bot"

    res = client.post("/verify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["prediction"] == "Bot"
    assert data["gate"] == "hard_rule"
    assert data["confidence"] == 1.0
    assert data["agent_assessment"] == "bot"
    assert data["risk_level"] == "high"

# 3. Hard-Rule Path
def test_hard_rule_path(client):
    cid = get_challenge_token(client)
    naive_bot_payload = {
        "challenge_id": cid,
        "avg_mouse_speed": 3500.0,
        "mouse_path_entropy": 0.01,
        "click_delay": 0.02,
        "task_completion_time": 0.1,
        "idle_time": 0.0,
        "micro_jitter_variance": 0.01,
        "acceleration_curve": 10.0,
        "curvature_variance": 0.0001,
        "overshoot_correction_ratio": 0.0001,
        "timing_entropy": 0.02,
    }
    res = client.post("/verify", json=naive_bot_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["gate"] == "hard_rule"
    assert data["prediction"] == "Bot"

# 4. ML Path
def test_ml_path(client, sample_human_features):
    cid = get_challenge_token(client)
    payload = dict(sample_human_features)
    payload["challenge_id"] = cid
    res = client.post("/verify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["gate"] in ("ml", "fallback")

# 5, 6, 7. Memory Progression: No Memory -> Retain -> Relevant Memory Exists & Influences Assessment
def test_memory_progression_and_influence(client, sample_human_features):
    scoped_bank = "test-progression-bank"

    # Turn 1: Fresh bank, zero memory
    cid1 = get_challenge_token(client)
    payload1 = dict(sample_human_features)
    payload1["challenge_id"] = cid1
    payload1["bank_id"] = scoped_bank

    res1 = client.post("/verify", json=payload1)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["memory_used"] is False
    assert data1["recalled_memory_count"] == 0
    assert "ZERO_HISTORY_BASELINE" in data1["reason_codes"]
    assert data1["retain_status"] == "retained"

    # Turn 2: Subsequent interaction in the same bank
    cid2 = get_challenge_token(client)
    payload2 = dict(sample_human_features)
    payload2["challenge_id"] = cid2
    payload2["bank_id"] = scoped_bank

    res2 = client.post("/verify", json=payload2)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["recalled_memory_count"] >= 1
    assert data2["memory_used"] is True
    assert "HISTORICAL_HUMAN_CONSISTENCY" in data2["reason_codes"]
    assert "consistent human" in data2["historical_context"].lower()

# 8. Hindsight Unavailable Fallback
def test_hindsight_unavailable_fallback(client, sample_human_features, monkeypatch):
    from config import config
    monkeypatch.setattr(config, "enable_memory", False)

    cid = get_challenge_token(client)
    payload = dict(sample_human_features)
    payload["challenge_id"] = cid

    res = client.post("/verify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["prediction"] == "Human"
    assert data["memory_status"] == "disabled"
    assert data["memory_used"] is False

# 9. Hindsight Recall Failure Fallback
def test_hindsight_recall_failure(client, sample_human_features, monkeypatch):
    def failing_recall(*args, **kwargs):
        raise RuntimeError("Simulated network drop during recall")

    monkeypatch.setattr(hindsight_service, "recall", failing_recall)

    cid = get_challenge_token(client)
    payload = dict(sample_human_features)
    payload["challenge_id"] = cid

    res = client.post("/verify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["prediction"] == "Human"
    assert data["memory_status"] == "error"
    assert data["memory_used"] is False

# 10. Hindsight Retain Failure Safe Verification
def test_hindsight_retain_failure(client, sample_human_features, monkeypatch):
    def failing_retain(*args, **kwargs):
        raise RuntimeError("Simulated database disk full during retain")

    monkeypatch.setattr(hindsight_service, "retain", failing_retain)

    cid = get_challenge_token(client)
    payload = dict(sample_human_features)
    payload["challenge_id"] = cid

    res = client.post("/verify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["prediction"] == "Human"
    assert data["retain_status"] == "failed"

# 11. LLM Unavailable Fallback
def test_llm_unavailable_fallback(client, sample_human_features, monkeypatch):
    def failing_llm(*args, **kwargs):
        raise RuntimeError("LLM rate limit / timeout")

    monkeypatch.setattr(security_agent, "_assess_with_llm", failing_llm)

    cid = get_challenge_token(client)
    payload = dict(sample_human_features)
    payload["challenge_id"] = cid

    res = client.post("/verify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["prediction"] == "Human"
    assert data["agent_assessment"] == "human"

# 12. Challenge Expired
def test_challenge_expired(client, sample_human_features):
    expired_cid = "expired_token_998877"
    challenges[expired_cid] = time.time() - 400 # 400 seconds ago (> 300)

    payload = dict(sample_human_features)
    payload["challenge_id"] = expired_cid

    res = client.post("/verify", json=payload)
    assert res.status_code == 403
    assert "expired" in res.json().get("detail", "").lower()

# 13. Challenge Reused
def test_challenge_reused(client, sample_human_features):
    cid = get_challenge_token(client)
    payload = dict(sample_human_features)
    payload["challenge_id"] = cid

    # First attempt succeeds
    res1 = client.post("/verify", json=payload)
    assert res1.status_code == 200

    # Second attempt with same token fails
    res2 = client.post("/verify", json=payload)
    assert res2.status_code == 403
    assert "invalid or expired" in res2.json().get("detail", "").lower()

# 14. Invalid Challenge
def test_invalid_challenge(client, sample_human_features):
    payload = dict(sample_human_features)
    payload["challenge_id"] = "non_existent_fake_token_123"

    res = client.post("/verify", json=payload)
    assert res.status_code == 403
    assert "invalid or expired" in res.json().get("detail", "").lower()

# 15. Missing Challenge
def test_missing_challenge(client, sample_human_features):
    payload = dict(sample_human_features)
    # challenge_id omitted
    res = client.post("/verify", json=payload)
    assert res.status_code == 400
    assert "missing challenge_id" in res.json().get("detail", "").lower()
