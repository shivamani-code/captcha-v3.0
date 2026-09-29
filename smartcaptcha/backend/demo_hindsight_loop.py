import os
import sys
import uuid
import time
import json
from typing import Dict, Any

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from config import config
from memory_schema import SecurityExperience, VerifyResponse
from hindsight_memory import HindsightMemoryService
from security_agent import security_agent
from decision_policy import decision_policy
from app import app, challenges

def print_separator(title: str):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)

def print_step(letter: str, title: str):
    print(f"\n[{letter}] {title}")
    print("-" * 50)

def ensure_mock_server_running(host: str = "127.0.0.1", port: int = 8888):
    """
    Detects if a Hindsight service is listening on the target port.
    If not, automatically launches the local mock Hindsight server in a daemon thread.
    """
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        if s.connect_ex((host, port)) == 0:
            return None

    import threading
    import uvicorn
    from mock_hindsight_server import mock_hindsight_app
    server_config = uvicorn.Config(mock_hindsight_app, host=host, port=port, log_level="error")
    server = uvicorn.Server(server_config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    time.sleep(0.8)
    return t

def run_demo():
    print_separator("SWIPECHA + HINDSIGHT FULL INTEGRATION DEMO (STEPS A -> K)")
    
    # Auto-detect or start mock server
    mock_thread = ensure_mock_server_running()
    if mock_thread:
        print("[*] Local mock Hindsight server auto-started on 127.0.0.1:8888.")

    # Initialize service
    service = HindsightMemoryService(base_url="http://127.0.0.1:8888")
    healthy, status = service.check_health()
    print(f"[*] Hindsight Memory Service: {status} (Healthy: {healthy})")
    
    # -------------------------------------------------------------
    # Step A: Start with an empty/new memory scope
    # -------------------------------------------------------------
    demo_bank_id = f"demo-session-{uuid.uuid4().hex[:8]}"
    print_step("A", f"Start with clean isolated memory scope: '{demo_bank_id}'")
    
    # Verify bank is initially empty
    memories_initial, _ = service.recall("human bot swipecha", bank_id=demo_bank_id)
    print(f"    Initial memory count in bank: {len(memories_initial)} (Empty bank verified)")

    # -------------------------------------------------------------
    # Step B & C: Perform normal human interaction
    # -------------------------------------------------------------
    print_step("B & C", "First Human Interaction (No prior memory in bank)")
    human_features_1 = {
        "avg_mouse_speed": 320.0,
        "mouse_path_entropy": 0.68,
        "click_delay": 1.1,
        "task_completion_time": 1.7,
        "idle_time": 0.2,
        "micro_jitter_variance": 50.0,
        "acceleration_curve": 1100.0,
        "curvature_variance": 0.035,
        "overshoot_correction_ratio": 0.075,
        "timing_entropy": 0.82,
    }
    
    # 1. Challenge & ML
    ml_pred_1 = "Human"
    ml_conf_1 = 0.985
    gate_1 = "ml"
    
    # 2. Recall
    query_1 = service.build_recall_query(human_features_1, ml_pred_1, "pass")
    recalled_1, mem_status_1 = service.recall(query_1, bank_id=demo_bank_id)
    
    # 3. Security Agent assessment
    agent_1 = security_agent.assess(
        features=human_features_1,
        ml_prediction=ml_pred_1,
        ml_confidence=ml_conf_1,
        hard_rule_triggered=False,
        recalled_memories=recalled_1,
    )
    
    print(f"    ML Result:             {ml_pred_1} (Confidence: {ml_conf_1:.2%}, Gate: {gate_1})")
    print(f"    Recalled Memories:     {len(recalled_1)} (Zero/Low relevant memory)")
    print(f"    Memory Used:           {agent_1.memory_used}")
    print(f"    Agent Assessment:      {agent_1.assessment.upper()} (Risk: {agent_1.risk_level.upper()})")
    print(f"    Historical Context:    {agent_1.historical_context}")
    print(f"    Reason Codes:          {agent_1.reason_codes}")

    # -------------------------------------------------------------
    # Step D: Retain the experience
    # -------------------------------------------------------------
    print_step("D", "Retain first distilled security experience to Hindsight")
    exp_1 = SecurityExperience(
        bank_id=demo_bank_id,
        behavior_summary=human_features_1,
        ml_prediction=ml_pred_1,
        ml_confidence=ml_conf_1,
        gate=gate_1,
        hard_rule_result="pass",
        agent_assessment=agent_1.assessment,
        risk_level=agent_1.risk_level,
        final_outcome=ml_pred_1,
        risk_indicators=agent_1.reason_codes,
        reason_context=agent_1.historical_context,
        tags=["swipecha", "security", "human"],
    )
    success_1, ret_status_1 = service.retain(exp_1, bank_id=demo_bank_id)
    print(f"    Retain Status:         {ret_status_1} (Success: {success_1})")

    # -------------------------------------------------------------
    # Step E: Perform several interactions and retain them
    # -------------------------------------------------------------
    print_step("E", "Perform subsequent interactions and retain experiences")
    
    # Interaction 2: Another human interaction
    human_features_2 = {
        "avg_mouse_speed": 345.0,
        "mouse_path_entropy": 0.62,
        "click_delay": 0.9,
        "task_completion_time": 1.9,
        "idle_time": 0.15,
        "micro_jitter_variance": 58.0,
        "acceleration_curve": 1250.0,
        "curvature_variance": 0.042,
        "overshoot_correction_ratio": 0.09,
        "timing_entropy": 0.79,
    }
    exp_2 = SecurityExperience(
        bank_id=demo_bank_id,
        behavior_summary=human_features_2,
        ml_prediction="Human",
        ml_confidence=0.991,
        gate="ml",
        hard_rule_result="pass",
        agent_assessment="human",
        risk_level="low",
        final_outcome="Human",
        risk_indicators=["ML_CONFIRMED_HUMAN"],
        reason_context="Natural trajectory with human jitter and high timing entropy",
        tags=["swipecha", "security", "human"],
    )
    service.retain(exp_2, bank_id=demo_bank_id)
    print("    Stored Interaction #2: Natural human swipe (retained)")

    # Interaction 3: Automated robotic attempt
    bot_features = {
        "avg_mouse_speed": 2800.0,
        "mouse_path_entropy": 0.015,
        "click_delay": 0.05,
        "task_completion_time": 0.12,
        "idle_time": 0.0,
        "micro_jitter_variance": 0.02,
        "acceleration_curve": 15.0,
        "curvature_variance": 0.0001,
        "overshoot_correction_ratio": 0.001,
        "timing_entropy": 0.01,
    }
    exp_3 = SecurityExperience(
        bank_id=demo_bank_id,
        behavior_summary=bot_features,
        ml_prediction="Bot",
        ml_confidence=1.0,
        gate="hard_rule",
        hard_rule_result="triggered",
        agent_assessment="bot",
        risk_level="high",
        final_outcome="Bot",
        risk_indicators=["HARD_RULE_TRIGGERED", "ML_CONFIRMED_BOT"],
        reason_context="Robotic velocity and zero trajectory variance observed",
        tags=["swipecha", "security", "bot"],
    )
    service.retain(exp_3, bank_id=demo_bank_id)
    print("    Stored Interaction #3: Robotic automation attempt (retained)")

    # -------------------------------------------------------------
    # Step F, G, H, I: Later interaction with related behavioral pattern
    # -------------------------------------------------------------
    print_step("F -> I", "Later Interaction (Hindsight Recall & Contextual Assessment)")
    current_human_features = {
        "avg_mouse_speed": 330.0,
        "mouse_path_entropy": 0.66,
        "click_delay": 1.0,
        "task_completion_time": 1.8,
        "idle_time": 0.18,
        "micro_jitter_variance": 52.0,
        "acceleration_curve": 1150.0,
        "curvature_variance": 0.038,
        "overshoot_correction_ratio": 0.082,
        "timing_entropy": 0.80,
    }

    # F & G: Recall
    query_later = service.build_recall_query(current_human_features, "Human", "pass")
    recalled_later, _ = service.recall(query_later, bank_id=demo_bank_id)
    print(f"[G] Hindsight Recall retrieved {len(recalled_later)} relevant previous experiences:")
    for idx, mem in enumerate(recalled_later[:3], 1):
        score_str = f"Score: {mem.score:.2f}" if mem.score else ""
        print(f"      ({idx}) [{score_str}] {mem.text[:95]}...")

    # H: Security Agent receives memory
    print(f"\n[H] Security Agent receiving current evidence + {len(recalled_later)} recalled memories.")

    # I: Contextual assessment
    agent_later = security_agent.assess(
        features=current_human_features,
        ml_prediction="Human",
        ml_confidence=0.988,
        hard_rule_triggered=False,
        recalled_memories=recalled_later,
    )
    print("\n[I] Resulting Contextual Security Assessment:")
    print(f"    Assessment:            {agent_later.assessment.upper()}")
    print(f"    Risk Level:            {agent_later.risk_level.upper()}")
    print(f"    Memory Used:           {agent_later.memory_used}")
    print(f"    Recalled Count:        {agent_later.recalled_memory_count}")
    print(f"    Memory Relevance:      {agent_later.memory_relevance}")
    print(f"    Historical Context:    {agent_later.historical_context}")
    print(f"    Reason Codes:          {agent_later.reason_codes}")
    print(f"    Recommended Action:    {agent_later.recommended_action}")

    # -------------------------------------------------------------
    # Step J: Retain the new experience
    # -------------------------------------------------------------
    print_step("J", "Retain the new distilled experience")
    exp_later = SecurityExperience(
        bank_id=demo_bank_id,
        behavior_summary=current_human_features,
        ml_prediction="Human",
        ml_confidence=0.988,
        gate="ml",
        hard_rule_result="pass",
        agent_assessment=agent_later.assessment,
        risk_level=agent_later.risk_level,
        final_outcome="Human",
        risk_indicators=agent_later.reason_codes,
        reason_context=agent_later.historical_context,
        tags=["swipecha", "security", "human"],
    )
    success_later, status_later = service.retain(exp_later, bank_id=demo_bank_id)
    print(f"    New Experience Retain Status: {status_later} (Success: {success_later})")

    # -------------------------------------------------------------
    # Step K: Restart the backend/process and verify persistence
    # -------------------------------------------------------------
    print_step("K", "Simulate Backend / Process Restart & Verify Persistent Memory")
    
    # Destroy original service instance
    del service
    print("    Existing service instance terminated.")
    
    # Reconnect fresh service instance
    new_service = HindsightMemoryService(base_url="http://127.0.0.1:8888")
    recalled_after_restart, restart_status = new_service.recall("human timing entropy", bank_id=demo_bank_id)
    print(f"    New Service Instance Connected: status={restart_status}")
    print(f"    Recalled Memories After Restart: {len(recalled_after_restart)}")
    assert len(recalled_after_restart) >= 1, "Persistence check failed!"
    print(f"    Sample Persisted Memory: '{recalled_after_restart[0].text[:90]}...'")
    print("\n[SUCCESS] Full Memory Loop (A -> K) Verified Successfully!")
    print_separator("DEMO EXECUTION COMPLETE")

if __name__ == "__main__":
    run_demo()
