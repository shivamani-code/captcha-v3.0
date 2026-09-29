import time
import json
import sys
import os

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in [repo_root, backend_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi.testclient import TestClient
from smartcaptcha.backend.demo_hindsight_loop import ensure_mock_server_running
from smartcaptcha.backend.hindsight_memory import HindsightMemoryService

print("--- STEP 1: START CLEAN & ENSURE MOCK BACKEND ---")
ensure_mock_server_running()

release_bank = f"release-bank-{int(time.time())}"
print(f"Active release bank: {release_bank}")

from smartcaptcha.backend.app import app, hindsight_service

hindsight_service.circuit_breaker.reset()
client = TestClient(app)

print("\n--- STEP 2: CREATE CHALLENGE 1 ---")
ch1 = client.get("/challenge").json()
cid1 = ch1["challenge_id"]
print(f"Challenge 1 Token: {cid1}")

print("\n--- STEP 3: FIRST HUMAN INTERACTION (Turn 1: Zero-Memory Baseline) ---")
payload1 = {
    "challenge_id": cid1,
    "bank_id": release_bank,
    "avg_mouse_speed": 1.15,
    "mouse_path_entropy": 0.75,
    "click_delay": 0.35,
    "task_completion_time": 1.45,
    "idle_time": 0.20,
    "micro_jitter_variance": 0.04,
    "acceleration_curve": 0.12,
    "curvature_variance": 0.08,
    "overshoot_correction_ratio": 0.03,
    "timing_entropy": 0.45,
}
t0 = time.perf_counter()
res1 = client.post("/verify", json=payload1)
lat1 = (time.perf_counter() - t0) * 1000
data1 = res1.json()

print(f"Response Status:        {res1.status_code}")
print(f"Latency:                {lat1:.2f} ms")
print(f"Prediction:             {data1['prediction']}")
print(f"Confidence:             {data1['confidence']}")
print(f"Gate:                   {data1['gate']}")
print(f"Memory Status:          {data1['memory_status']}")
print(f"Memory Used:            {data1['memory_used']}")
print(f"Recalled Memory Count:  {data1['recalled_memory_count']}")
print(f"Agent Assessment:       {data1['agent_assessment']}")
print(f"Risk Level:             {data1['risk_level']}")
print(f"Historical Context:     {data1['historical_context']}")
print(f"Reason Codes:           {data1['reason_codes']}")
print(f"Recommended Action:     {data1['recommended_action']}")
print(f"Retain Status:          {data1['retain_status']}")

assert res1.status_code == 200
assert data1["prediction"] == "Human"
assert data1["memory_used"] is False
assert data1["recalled_memory_count"] == 0
assert "ZERO_HISTORY_BASELINE" in data1["reason_codes"]

time.sleep(0.5)

print("\n--- STEP 4: SECOND RELATED INTERACTION (Turn 2: Recalled Memory Informs Agent) ---")
ch2 = client.get("/challenge").json()
cid2 = ch2["challenge_id"]

payload2 = {
    "challenge_id": cid2,
    "bank_id": release_bank,
    "avg_mouse_speed": 1.18,
    "mouse_path_entropy": 0.72,
    "click_delay": 0.33,
    "task_completion_time": 1.40,
    "idle_time": 0.18,
    "micro_jitter_variance": 0.05,
    "acceleration_curve": 0.11,
    "curvature_variance": 0.07,
    "overshoot_correction_ratio": 0.02,
    "timing_entropy": 0.44,
}
t0 = time.perf_counter()
res2 = client.post("/verify", json=payload2)
lat2 = (time.perf_counter() - t0) * 1000
data2 = res2.json()

print(f"Response Status:        {res2.status_code}")
print(f"Latency:                {lat2:.2f} ms")
print(f"Prediction:             {data2['prediction']}")
print(f"Confidence:             {data2['confidence']}")
print(f"Memory Used:            {data2['memory_used']}")
print(f"Recalled Memory Count:  {data2['recalled_memory_count']}")
print(f"Agent Assessment:       {data2['agent_assessment']}")
print(f"Risk Level:             {data2['risk_level']}")
print(f"Historical Context:     {data2['historical_context']}")
print(f"Reason Codes:           {data2['reason_codes']}")
print(f"Recommended Action:     {data2['recommended_action']}")

assert res2.status_code == 200
assert data2["memory_used"] is True
assert data2["recalled_memory_count"] >= 1
assert "HISTORICAL_HUMAN_CONSISTENCY" in data2["reason_codes"]

time.sleep(0.5)

print("\n--- STEP 5: SIMULATE PROCESS RESTART ---")
del hindsight_service
fresh_hindsight = HindsightMemoryService()
print(f"Fresh Hindsight Service connected: {fresh_hindsight.check_health()}")

from smartcaptcha.backend import app as backend_app_module
backend_app_module.hindsight_service = fresh_hindsight
restarted_client = TestClient(backend_app_module.app)

print("\n--- STEP 6: THIRD RELATED INTERACTION (Turn 3: Post-Restart Persistent Memory) ---")
ch3 = restarted_client.get("/challenge").json()
cid3 = ch3["challenge_id"]

payload3 = {
    "challenge_id": cid3,
    "bank_id": release_bank,
    "avg_mouse_speed": 1.12,
    "mouse_path_entropy": 0.73,
    "click_delay": 0.32,
    "task_completion_time": 1.48,
    "idle_time": 0.19,
    "micro_jitter_variance": 0.04,
    "acceleration_curve": 0.11,
    "curvature_variance": 0.08,
    "overshoot_correction_ratio": 0.03,
    "timing_entropy": 0.43,
}
t0 = time.perf_counter()
res3 = restarted_client.post("/verify", json=payload3)
lat3 = (time.perf_counter() - t0) * 1000
data3 = res3.json()

print(f"Response Status:        {res3.status_code}")
print(f"Latency:                {lat3:.2f} ms")
print(f"Prediction:             {data3['prediction']}")
print(f"Confidence:             {data3['confidence']}")
print(f"Memory Used:            {data3['memory_used']}")
print(f"Recalled Memory Count:  {data3['recalled_memory_count']}")
print(f"Agent Assessment:       {data3['agent_assessment']}")
print(f"Risk Level:             {data3['risk_level']}")
print(f"Historical Context:     {data3['historical_context']}")
print(f"Reason Codes:           {data3['reason_codes']}")
print(f"Recommended Action:     {data3['recommended_action']}")

assert res3.status_code == 200
assert data3["memory_used"] is True
assert data3["recalled_memory_count"] >= 2
assert "HISTORICAL_HUMAN_CONSISTENCY" in data3["reason_codes"]

print("\n============================================================")
print("  PHASE 18 END-TO-END RELEASE VERIFICATION: COMPLETE SUCCESS")
print("============================================================")
