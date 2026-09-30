import os
import sys
import logging
import time
import uuid
import math
import joblib
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

# Ensure backend directory is in path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from config import config
from memory_schema import SecurityExperience, VerifyResponse
from hindsight_memory import hindsight_service
from security_agent import security_agent
from decision_policy import decision_policy

logger = logging.getLogger("swipecha.backend")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="SwipeCHA Backend")

# --------------------------------------------------
# CORS SETTINGS (configurable via CORS_ALLOWED_ORIGINS, default allow_origins=["*"])
# --------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# CHALLENGE TOKEN STORAGE
# --------------------------------------------------
challenges: Dict[str, float] = {}

def cleanup_challenges():
    now = time.time()
    expired = [cid for cid, t in list(challenges.items()) if now - t > config.challenge_timeout_seconds]
    for cid in expired:
        challenges.pop(cid, None)

# --------------------------------------------------
# MODEL CONFIG
# --------------------------------------------------
MODEL_PATH = os.path.join(backend_dir, "captcha_model.pkl")

# All 10 features the frontend sends — must match train_model.py FEATURE_COLUMNS
FEATURE_COLUMNS = [
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

if os.path.exists(MODEL_PATH):
    model = joblib.load(MODEL_PATH)
    MODEL_LOADED = True
    print(f"[OK] Model loaded from {MODEL_PATH}")
    print(f"   Expected features: {model.n_features_in_}")
else:
    model = None
    MODEL_LOADED = False
    print(f"[WARN] ML model missing at {MODEL_PATH} — running in safe fallback mode")


# --------------------------------------------------
# HEALTH CHECK ENDPOINT
# --------------------------------------------------
@app.get("/health")
def health():
    h_healthy, h_status = hindsight_service.check_health()
    return {
        "status": "ok",
        "service": "SwipeTCHA backend",
        "model_loaded": MODEL_LOADED if "MODEL_LOADED" in globals() else False,
        "hindsight_healthy": h_healthy,
        "hindsight_status": h_status,
    }


# --------------------------------------------------
# MEMORY STATUS / OBSERVABILITY ENDPOINT
# --------------------------------------------------
@app.get("/memory/status")
def get_memory_status():
    h_healthy, h_status = hindsight_service.check_health()
    return {
        "status": "ok",
        "memory_enabled": config.enable_memory,
        "security_agent_enabled": config.enable_security_agent,
        "hindsight_api_url": config.hindsight_api_url,
        "hindsight_bank_id": config.hindsight_default_bank_id,
        "hindsight_healthy": h_healthy,
        "hindsight_status": h_status,
    }


# --------------------------------------------------
# CHALLENGE ENDPOINT
# --------------------------------------------------
@app.get("/challenge")
def get_challenge():
    cleanup_challenges()
    challenge_id = uuid.uuid4().hex
    challenges[challenge_id] = time.time()
    return {"challenge_id": challenge_id}


# --------------------------------------------------
# ROOT ENDPOINT
# --------------------------------------------------
@app.get("/")
def root():
    return {
        "status": "backend alive",
        "model_loaded": MODEL_LOADED,
        "features": FEATURE_COLUMNS,
    }


# --------------------------------------------------
# VERIFY ENDPOINT — STEP 5: FULL INTEGRATION
# --------------------------------------------------
@app.post("/verify")
def verify(payload: dict, background_tasks: BackgroundTasks = None):
    cleanup_challenges()

    # 1, 2, 3. CHALLENGE VALIDATION & CONSUMPTION
    challenge_id = payload.get("challenge_id")

    if not challenge_id:
        raise HTTPException(status_code=400, detail="Missing challenge_id")

    if challenge_id not in challenges:
        raise HTTPException(status_code=403, detail="Invalid or expired challenge_id")

    creation_time = challenges.pop(challenge_id)

    if time.time() - creation_time > config.challenge_timeout_seconds:
        raise HTTPException(status_code=403, detail="Expired challenge_id")

    # 4. FEATURE EXTRACTION & STRICT FINITE VALUE VALIDATION (PRIORITY 1)
    features_dict: Dict[str, float] = {}
    for col in FEATURE_COLUMNS:
        raw_val = payload.get(col, 0.0)
        try:
            val = float(raw_val)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=f"Feature extraction error for {col}: {exc}")
        if not math.isfinite(val):
            raise HTTPException(status_code=422, detail=f"Feature {col} must be a finite number")
        features_dict[col] = val

    speed = features_dict.get("avg_mouse_speed", 0.0)
    entropy = features_dict.get("mouse_path_entropy", 1.0)
    delay = features_dict.get("click_delay", 1.0)
    dur = features_dict.get("task_completion_time", 1.0)
    jitter = features_dict.get("micro_jitter_variance", 1.0)
    timing_h = features_dict.get("timing_entropy", 1.0)

    # 5. HARD BOT RULE FIRST GATE
    naive_bot = (
        speed > 2.2 and
        entropy < 0.08 and
        delay < 0.2 and
        dur < 0.8 and
        jitter < 0.2 and
        timing_h < 0.10
    )

    # 6. RUN HARD-RULE OR ML INFERENCE
    if naive_bot:
        ml_prediction = "Bot"
        ml_confidence = 1.0
        gate = "hard_rule"
        hard_rule_status = "triggered"
    elif not MODEL_LOADED:
        ml_prediction = "Human"
        ml_confidence = 0.5
        gate = "fallback"
        hard_rule_status = "pass"
    else:
        feature_vector = [[features_dict[col] for col in FEATURE_COLUMNS]]
        prediction_val = model.predict(feature_vector)[0]
        proba = model.predict_proba(feature_vector)[0]
        confidence_val = float(max(proba))
        ml_prediction = "Human" if int(prediction_val) == 1 else "Bot"
        ml_confidence = round(confidence_val, 4)
        gate = "ml"
        hard_rule_status = "pass"

    # Memory Bank ID (isolated by scope or default bank)
    bank_id = payload.get("bank_id") or config.hindsight_default_bank_id

    # 7, 8, 9. HINDSIGHT RECALL (PRIORITY 3: Skip recall if hard rule triggered)
    recalled_memories = []
    if naive_bot:
        memory_status = "skipped"
    elif config.enable_memory:
        try:
            recall_query = hindsight_service.build_recall_query(features_dict, ml_prediction, hard_rule_status)
            recalled_memories, memory_status = hindsight_service.recall(
                query=recall_query,
                bank_id=bank_id,
            )
        except Exception as e:
            logger.warning(f"Hindsight recall failure: {e}; continuing with baseline ML.")
            recalled_memories = []
            memory_status = "error"
    else:
        memory_status = "disabled"

    # 10, 11. PASS EVIDENCE TO SECURITY AGENT
    agent_assessment = None
    if config.enable_security_agent:
        try:
            agent_assessment = security_agent.assess(
                features=features_dict,
                ml_prediction=ml_prediction,
                ml_confidence=ml_confidence,
                hard_rule_triggered=naive_bot,
                recalled_memories=recalled_memories,
            )
        except Exception as e:
            logger.warning(f"Security Agent assessment failure: {e}; falling back to baseline.")
            agent_assessment = None

    # 12. DETERMINE FINAL COMPATIBLE CAPTCHA RESULT
    response_obj = decision_policy.build_response(
        prediction=ml_prediction,
        confidence=ml_confidence,
        gate=gate,
        agent_assessment=agent_assessment,
        memory_status=memory_status,
        retain_status=None,
    )

    # 13. HINDSIGHT RETAIN (distilled useful experience)
    retain_status = "skipped"
    if config.enable_memory:
        try:
            experience = SecurityExperience(
                bank_id=bank_id,
                behavior_summary=features_dict,
                ml_prediction=ml_prediction,
                ml_confidence=ml_confidence,
                gate=gate,
                hard_rule_result=hard_rule_status,
                agent_assessment=agent_assessment.assessment if agent_assessment else "unavailable",
                risk_level=agent_assessment.risk_level if agent_assessment else ("low" if ml_prediction == "Human" else "high"),
                final_outcome=ml_prediction,
                risk_indicators=agent_assessment.reason_codes if agent_assessment else [],
                reason_context=agent_assessment.historical_context if agent_assessment else "Baseline evaluation",
                tags=["swipecha", "security", ml_prediction.lower()],
            )
            if background_tasks and config.hindsight_async_retain:
                background_tasks.add_task(hindsight_service.retain, experience, bank_id)
                retain_status = "retained"
            else:
                _, retain_status = hindsight_service.retain(
                    experience=experience,
                    bank_id=bank_id,
                )
        except Exception as e:
            logger.warning(f"Hindsight retain failure: {e}; verification finishes safely.")
            retain_status = "failed"

    # 14. RETURN COMPATIBLE RESPONSE
    result_dict = response_obj.model_dump()
    result_dict["retain_status"] = retain_status
    return result_dict


if __name__ == "__main__":
    import uvicorn
    hindsight_service._init_client()
    uvicorn.run(app, host="127.0.0.1", port=8000)

