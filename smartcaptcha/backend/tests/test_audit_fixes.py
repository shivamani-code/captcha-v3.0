import time
import math
import pytest
from app import challenges
from hindsight_memory import hindsight_service
from security_agent import security_agent
from memory_schema import RecalledMemoryItem

def get_challenge_token(client):
    res = client.get("/challenge")
    assert res.status_code == 200
    return res.json()["challenge_id"]

# =========================================================================
# Priority 1: Non-Finite Feature Inputs (NaN, Inf, -Inf) Validation Tests
# =========================================================================

def test_nan_feature_rejected_422(client, sample_human_features):
    cid = get_challenge_token(client)
    payload = dict(sample_human_features)
    payload["challenge_id"] = cid
    payload["avg_mouse_speed"] = "NaN"

    res = client.post("/verify", json=payload)
    assert res.status_code == 422
    detail = res.json().get("detail", "")
    assert "finite" in detail.lower() or "invalid" in detail.lower()

def test_inf_feature_rejected_422(client, sample_human_features):
    cid = get_challenge_token(client)
    payload = dict(sample_human_features)
    payload["challenge_id"] = cid
    payload["avg_mouse_speed"] = "inf"

    res = client.post("/verify", json=payload)
    assert res.status_code == 422
    detail = res.json().get("detail", "")
    assert "finite" in detail.lower() or "invalid" in detail.lower()

def test_negative_inf_feature_rejected_422(client, sample_human_features):
    cid = get_challenge_token(client)
    payload = dict(sample_human_features)
    payload["challenge_id"] = cid
    payload["acceleration_curve"] = "-Infinity"

    res = client.post("/verify", json=payload)
    assert res.status_code == 422
    detail = res.json().get("detail", "")
    assert "finite" in detail.lower() or "invalid" in detail.lower()

def test_string_inf_rejected_422(client, sample_human_features):
    cid = get_challenge_token(client)
    payload = dict(sample_human_features)
    payload["challenge_id"] = cid
    payload["micro_jitter_variance"] = "Infinity"

    res = client.post("/verify", json=payload)
    assert res.status_code == 422
    detail = res.json().get("detail", "")
    assert "finite" in detail.lower() or "invalid" in detail.lower()

# =========================================================================
# Priority 2: Circuit Breaker and Outage Latency Elimination Tests
# =========================================================================

def test_circuit_breaker_fast_bypass_under_50ms(sample_human_features):
    cb = hindsight_service.circuit_breaker
    cb.trip()
    assert cb.is_open() is True

    # Recall must fast-bypass in < 20ms without network call
    t0 = time.time()
    recalled, status = hindsight_service.recall("test query", bank_id="cb-test-bank")
    duration_recall = time.time() - t0

    assert status == "unavailable"
    assert recalled == []
    assert duration_recall < 0.05, f"Recall took too long during circuit trip: {duration_recall}s"

    # Retain must fast-bypass in < 20ms without network call
    from memory_schema import SecurityExperience
    exp = SecurityExperience(
        bank_id="cb-test-bank",
        behavior_summary=sample_human_features,
        ml_prediction="Human",
        ml_confidence=0.98,
        gate="ml",
        hard_rule_result="pass",
        agent_assessment="human",
        risk_level="low",
        final_outcome="Human",
        reason_context="Circuit breaker test",
    )
    t0 = time.time()
    success, ret_status = hindsight_service.retain(exp, bank_id="cb-test-bank")
    duration_retain = time.time() - t0

    assert success is False
    assert ret_status == "unavailable"
    assert duration_retain < 0.05, f"Retain took too long during circuit trip: {duration_retain}s"

    cb.reset()
    assert cb.is_open() is False

def test_circuit_breaker_state_transitions():
    from hindsight_memory import CircuitBreaker
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

    assert cb.is_open() is False
    assert cb.state == "CLOSED"

    # 1 failure: threshold not reached
    cb.record_failure()
    assert cb.is_open() is False
    assert cb.state == "CLOSED"

    # 2 failures: threshold reached -> trips to OPEN
    cb.record_failure()
    assert cb.state == "OPEN"
    assert cb.is_open() is True

    # Wait for recovery timeout
    time.sleep(0.15)

    # After recovery timeout -> enters HALF_OPEN
    assert cb.is_open() is False
    assert cb.state == "HALF_OPEN"

    # Recovery success -> resets to CLOSED
    cb.record_success()
    assert cb.state == "CLOSED"
    assert cb.failure_count == 0

# =========================================================================
# Priority 3: Hard-Rule Recall Optimization Tests
# =========================================================================

def test_hard_rule_skips_hindsight_recall(client, monkeypatch):
    recall_called = False

    def spy_recall(*args, **kwargs):
        nonlocal recall_called
        recall_called = True
        return [], "available"

    monkeypatch.setattr(hindsight_service, "recall", spy_recall)

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
    assert data["memory_status"] == "skipped"

    # Crucial assertion: Hindsight recall was NOT called
    assert recall_called is False, "Hindsight recall should be skipped on hard-rule trigger"

    # Crucial assertion: Retention was still performed
    assert data["retain_status"] == "retained"

# =========================================================================
# Priority 5: Secondary Challenge ("challenge_again") Verification
# =========================================================================

def test_borderline_evasion_triggers_challenge_again():
    # Borderline human velocity with low entropy
    borderline_features = {
        "avg_mouse_speed": 850.0,
        "mouse_path_entropy": 0.12,
        "click_delay": 0.6,
        "task_completion_time": 1.2,
        "idle_time": 0.05,
        "micro_jitter_variance": 8.0,
        "acceleration_curve": 800.0,
        "curvature_variance": 0.005,
        "overshoot_correction_ratio": 0.02,
        "timing_entropy": 0.35,
    }

    # Recalled bot memory from this scope
    bot_memory = RecalledMemoryItem(
        id="mem_bot_1",
        text="SwipeCHA verification outcome: Bot. ML=Bot, high risk robotic attack recorded.",
        tags=["swipecha", "bot"]
    )

    assessment = security_agent.assess(
        features=borderline_features,
        ml_prediction="Human",
        ml_confidence=0.75,
        hard_rule_triggered=False,
        recalled_memories=[bot_memory]
    )

    assert assessment.assessment == "uncertain"
    assert assessment.risk_level == "medium"
    assert assessment.recommended_action == "challenge_again"
    assert "HISTORICAL_BOT_FINGERPRINT_MATCH" in assessment.reason_codes
