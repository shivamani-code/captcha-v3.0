# SwipeCHA Production Deployment Guide

This guide provides instructions for deploying SwipeCHA with Hindsight persistent experience memory and the Security Agent.

---

## 1. System Architecture Overview

```
User Browser (HTML / JS Widget)
          │
          ▼  (HTTPS / REST)
FastAPI Backend (smartcaptcha/backend/app.py)
   ├── 1. Challenge Token Store (UUIDv4 single-use, 300s TTL)
   ├── 2. Input Sanitizer (math.isfinite bounds validation)
   ├── 3. Deterministic Hard-Rule Gate (high-velocity bot trap)
   ├── 4. Random Forest Classifier (captcha_model.pkl, 200 trees)
   ├── 5. Circuit Breaker (<2ms fast-bypass on outage)
   ├── 6. Hindsight Memory Service (hindsight-client 0.10.1)
   └── 7. Security Agent (Heuristic engine / OpenAI gpt-4o-mini)
```

---

## 2. Environment Variables Specification

Configure these variables in your deployment environment or container specification:

| Environment Variable | Type | Default | Production Value | Description |
|---|:---:|:---:|:---:|---|
| `HINDSIGHT_API_URL` | string | `http://127.0.0.1:8888` | `https://api.hindsight.vectorize.io` | URL of the Hindsight service or cluster |
| `HINDSIGHT_API_KEY` | string | `None` | `your_production_api_key` | Authentication token for Hindsight Cloud |
| `HINDSIGHT_BANK_ID` | string | `swipecha-security-bank` | `production-security-bank` | Default memory bank identifier |
| `HINDSIGHT_TIMEOUT` | float | `2.0` | `2.0` | Timeout in seconds for Hindsight HTTP requests |
| `HINDSIGHT_ASYNC_RETAIN` | bool | `false` | `true` | Retain memories in FastAPI `BackgroundTasks` |
| `HINDSIGHT_CIRCUIT_BREAKER_THRESHOLD` | int | `2` | `3` | Consecutive failures before tripping breaker |
| `HINDSIGHT_CIRCUIT_BREAKER_TIMEOUT` | float | `10.0` | `15.0` | Seconds to bypass Hindsight after tripping |
| `CORS_ALLOWED_ORIGINS` | string | `*` | `https://yourdomain.com` | Comma-separated list of allowed frontend origins |
| `SECURITY_AGENT_PROVIDER` | string | `heuristic` | `heuristic` or `openai` | Agent evaluation mode |
| `OPENAI_API_KEY` | string | `None` | `sk-...` | Optional API key for LLM assessment |
| `SECURITY_AGENT_MODEL` | string | `gpt-4o-mini` | `gpt-4o-mini` | LLM model identifier |
| `CHALLENGE_TIMEOUT_SECONDS` | int | `300` | `300` | Challenge token validity window (seconds) |

---

## 3. Deployment Modes

### Mode A: Local / Staging (Verified Baseline)
Uses the local Hindsight-compatible test backend.

```bash
# 1. Install dependencies
pip install -r smartcaptcha/backend/requirements.txt

# 2. Start mock Hindsight service (auto-started by demo loop, or run directly)
python smartcaptcha/backend/mock_hindsight_server.py --port 8888

# 3. Start SwipeCHA FastAPI verifier backend
uvicorn smartcaptcha.backend.app:app --host 0.0.0.0 --port 8000
```

### Mode B: Production (Commercial Hindsight Cloud)
Directs memory operations to the live Hindsight service.

1. Obtain a production Hindsight Cloud API key and endpoint.
2. Set environment variables in your cloud host (Docker, Kubernetes, Render, AWS ECS):
   ```bash
   export HINDSIGHT_API_URL="https://api.hindsight.vectorize.io"
   export HINDSIGHT_API_KEY="hnd_live_xxxxxxxxxxxxxxxx"
   export HINDSIGHT_BANK_ID="company-swipecha-bank"
   export HINDSIGHT_ASYNC_RETAIN="true"
   export CORS_ALLOWED_ORIGINS="https://app.yourcompany.com"
   ```
3. Launch FastAPI using production ASGI server:
   ```bash
   uvicorn smartcaptcha.backend.app:app --host 0.0.0.0 --port 8000 --workers 4
   ```

---

## 4. Health and Verification Probing

Configure your container orchestrator (Kubernetes, AWS ALB, Render) to probe:
- **Liveness & Readiness Endpoint:** `GET /health`
- **Expected Response (HTTP 200):**
  ```json
  {
    "status": "ok",
    "service": "SwipeTCHA backend",
    "model_loaded": true,
    "hindsight_healthy": true,
    "hindsight_status": "connected (API 0.10.1)",
    "circuit_breaker": "CLOSED",
    "memory_enabled": true,
    "security_agent_enabled": true
  }
  ```

---

## 5. Security Checklist Before Launch

- [x] All 10 feature values protected with `math.isfinite()` bounds checks (HTTP 422 on NaN/Inf).
- [x] Challenge tokens single-use and expiring after 300 seconds.
- [x] Replay attacks rejected with HTTP 403 Forbidden.
- [x] Outage circuit breaker fast-bypasses in < 2ms, preventing DDoS during downstream failure.
- [x] Zero raw mouse coordinates retained to memory banks.
- [x] CORS restricted to authorized frontend origins in production.
- [x] Secret scanning verified: no active API keys committed in repository.
