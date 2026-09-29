# SwipeCHA Final Empirical Test Results

**Date of Execution:** 2026-09-28  
**Environment:** Python 3.14.5 | Windows 11 | pytest 9.1.1 | Starlette TestClient  
**Total Validated Test Items:** **115**  
**Passed:** **115**  
**Failed:** **0**  
**Success Rate:** **100.0%**  

---

## 1. Test Suite Summary Table

| Test Suite | Command | Total | Passed | Failed | Duration | Status |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **Backend Pytest Suite** | `python -m pytest smartcaptcha/backend/tests -v` | 41 | 41 | 0 | 4.16s | **PASS** |
| **QA / Security Audit Suite** | `python tests/test_qa_security_suite.py` | 23 | 23 | 0 | 14.2s | **PASS** |
| **Stress & Security Gates** | `python reports/stress_test.py` | 34 | 34 | 0 | 8.8s | **PASS** |
| **Autonomous Demo Loop** | `python smartcaptcha/backend/demo_hindsight_loop.py` | 11 | 11 | 0 | 5.1s | **PASS** |
| **Release End-to-End Sequence** | `python smartcaptcha/backend/tests/run_release_test.py` | 6 | 6 | 0 | 5.8s | **PASS** |
| **GRAND TOTAL** | — | **115** | **115** | **0** | **38.06s** | **100% PASS** |

---

## 2. Pytest Detailed Results (41 Tests)

```text
smartcaptcha/backend/tests/test_audit_fixes.py::test_nan_feature_rejected_422 PASSED
smartcaptcha/backend/tests/test_audit_fixes.py::test_inf_feature_rejected_422 PASSED
smartcaptcha/backend/tests/test_audit_fixes.py::test_negative_inf_feature_rejected_422 PASSED
smartcaptcha/backend/tests/test_audit_fixes.py::test_string_inf_rejected_422 PASSED
smartcaptcha/backend/tests/test_audit_fixes.py::test_circuit_breaker_fast_bypass_under_50ms PASSED
smartcaptcha/backend/tests/test_audit_fixes.py::test_circuit_breaker_state_transitions PASSED
smartcaptcha/backend/tests/test_audit_fixes.py::test_hard_rule_skips_hindsight_recall PASSED
smartcaptcha/backend/tests/test_audit_fixes.py::test_borderline_evasion_triggers_challenge_again PASSED
smartcaptcha/backend/tests/test_hindsight_memory.py::test_hindsight_health_check PASSED
smartcaptcha/backend/tests/test_hindsight_memory.py::test_hindsight_retain_and_recall PASSED
smartcaptcha/backend/tests/test_hindsight_memory.py::test_hindsight_offline_fallback PASSED
smartcaptcha/backend/tests/test_hindsight_memory.py::test_hindsight_memory_disabled PASSED
smartcaptcha/backend/tests/test_memory_isolation.py::test_bank_isolation PASSED
smartcaptcha/backend/tests/test_persistence.py::test_memory_persists_across_instances PASSED
smartcaptcha/backend/tests/test_security_agent.py::test_zero_memory_human_baseline PASSED
smartcaptcha/backend/tests/test_security_agent.py::test_zero_memory_bot_baseline PASSED
smartcaptcha/backend/tests/test_security_agent.py::test_hard_rule_override PASSED
smartcaptcha/backend/tests/test_security_agent.py::test_recalled_memory_reaches_agent_human_reinforcement PASSED
smartcaptcha/backend/tests/test_security_agent.py::test_recalled_memory_reaches_agent_repeated_bot_attacks PASSED
smartcaptcha/backend/tests/test_security_agent.py::test_recalled_memory_contextualizes_borderline_evasion PASSED
smartcaptcha/backend/tests/test_security_agent.py::test_never_invent_historical_events PASSED
smartcaptcha/backend/tests/test_security_agent.py::test_llm_markdown_code_fence_cleaning PASSED
smartcaptcha/backend/tests/test_security_agent.py::test_malformed_llm_output_fallback PASSED
smartcaptcha/backend/tests/test_security_agent.py::test_llm_api_network_failure_fallback PASSED
smartcaptcha/backend/tests/test_security_agent.py::test_security_agent_input_model PASSED
smartcaptcha/backend/tests/test_security_agent.py::test_security_agent_dict_input PASSED
smartcaptcha/backend/tests/test_security_agent.py::test_edge_case_nan_and_missing_values PASSED
smartcaptcha/backend/tests/test_security_agent.py::test_schema_conformance_with_integration_contract PASSED
smartcaptcha/backend/tests/test_verify_memory_flow.py::test_normal_human_interaction PASSED
smartcaptcha/backend/tests/test_verify_memory_flow.py::test_bot_like_interaction PASSED
smartcaptcha/backend/tests/test_verify_memory_flow.py::test_hard_rule_path PASSED
smartcaptcha/backend/tests/test_verify_memory_flow.py::test_ml_path PASSED
smartcaptcha/backend/tests/test_verify_memory_flow.py::test_memory_progression_and_influence PASSED
smartcaptcha/backend/tests/test_verify_memory_flow.py::test_hindsight_unavailable_fallback PASSED
smartcaptcha/backend/tests/test_verify_memory_flow.py::test_hindsight_recall_failure PASSED
smartcaptcha/backend/tests/test_verify_memory_flow.py::test_hindsight_retain_failure PASSED
smartcaptcha/backend/tests/test_verify_memory_flow.py::test_llm_unavailable_fallback PASSED
smartcaptcha/backend/tests/test_verify_memory_flow.py::test_challenge_expired PASSED
smartcaptcha/backend/tests/test_verify_memory_flow.py::test_challenge_reused PASSED
smartcaptcha/backend/tests/test_verify_memory_flow.py::test_invalid_challenge PASSED
smartcaptcha/backend/tests/test_verify_memory_flow.py::test_missing_challenge PASSED
```

---

## 3. QA / Security Suite Detailed Results (23 Items)

```text
[Item 01] Baseline ML Pipeline              -> PASS (Accuracy: 99.84%, ROC-AUC: 1.0000)
[Item 02] ML Feature Order                   -> PASS (Exact 10 features match model training order)
[Item 03] Hard Bot Rule Gate                 -> PASS (Traps naive bot with confidence 1.0 and gate "hard_rule")
[Item 04] Hindsight Architecture Alignment  -> PASS (Official SDK imported, retain/recall methods conform)
[Item 05] Hindsight Retain Distillation     -> PASS (Only summary kinetic features and outcomes stored)
[Item 06] Hindsight Semantic Recall         -> PASS (Recall queries contain behavioral fingerprints)
[Item 07] Multi-Tenant Bank Scoping         -> PASS (Memories in bank_A are strictly isolated from bank_B)
[Item 08] Security Agent Schema Conformance -> PASS (All outputs validate against Pydantic schema)
[Item 09] Empty-Memory Baseline Behavior    -> PASS (memory_used=False, ZERO_HISTORY_BASELINE emitted)
[Item 10] Memory Reach to Agent             -> PASS (Recalled memory objects reach agent.assess())
[Item 11] Historical Context Influence      -> PASS (Past bot encounter escalates borderline swipe scrutiny)
[Item 12] Single-Use Challenge Tokens       -> PASS (Popped atomically; replay rejected with 403)
[Item 13] Challenge Token Expiry (>300s)    -> PASS (Tokens older than 300s rejected with 403)
[Item 14] Concurrent Challenge Race (20 th) -> PASS (Exactly 1 accepted, 19 rejected with 403)
[Item 15] PII & Raw Coordinate Omission     -> PASS (Raw coordinate arrays are never retained or logged)
[Item 16] Hardcoded Secrets Scan            -> PASS (Zero active keys or credentials found)
[Item 17] Fallback on Hindsight Outage      -> PASS (Fast-bypasses memory and returns 200 with pure ML)
[Item 18] Fallback on Agent / LLM Outage    -> PASS (Falls back to deterministic heuristic rules safely)
[Item 19] Cross-Process Persistence         -> PASS (Retained memories survive client destruction)
[Item 20] Developer Observability Panel     -> PASS (Details element correctly collapsed by default)
[Item 21] API Verification Endpoint         -> PASS (Root, health, challenge, verify, 422 validation pass)
[Item 22] Frontend Compatibility            -> PASS (Feature order and endpoint signatures match)
[Item 23] Deployment Configuration          -> PASS (Path resolution and dependencies verified clean)
```

---

## 4. Stress and Security Testing Results (34 Checks)

```text
Human attempts:    15 / 15 Accepted (0 false rejections)
Bot attempts:      15 / 15 Rejected (0 false acceptances)
Security gates:
  missing_id:      PASS (Status: 400 Bad Request)
  fake_id:         PASS (Status: 403 Forbidden)
  reused_id:       PASS (Status: 403 Forbidden)
  expired_id:      PASS (Status: 403 Forbidden)
```

---

## 5. End-to-End Release Sequence (Captured Outputs)

```text
[A] Start Clean Scope:           Bank 'release-bank-1790619597' initialized with 0 memories.
[B] Turn 1 (Human Baseline):     ML=Human (0.6401) | Recall=0 | MemUsed=False | ZERO_HISTORY_BASELINE | Retained.
[C] Turn 2 (Related Human):      ML=Human (0.6306) | Recall=1 | MemUsed=True  | HISTORICAL_HUMAN_CONSISTENCY | Retained.
[D] Process Restart Simulation:  Original client destroyed; fresh Hindsight service instantiated.
[E] Turn 3 (Post-Restart Human): ML=Human (0.6301) | Recall=2 | MemUsed=True  | HISTORICAL_HUMAN_CONSISTENCY | Retained.
[F] Persistence Verified:        Survives client destruction and retrieves 2 historical memories from disk.
```
