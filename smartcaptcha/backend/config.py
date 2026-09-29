import os
from typing import Optional
from pydantic import BaseModel

class AppConfig(BaseModel):
    # Hindsight Configuration
    hindsight_api_url: str = os.getenv("HINDSIGHT_API_URL", "http://127.0.0.1:8888")
    hindsight_api_key: Optional[str] = os.getenv("HINDSIGHT_API_KEY", None)
    hindsight_default_bank_id: str = os.getenv("HINDSIGHT_BANK_ID", "swipecha-security-bank")
    hindsight_timeout: float = float(os.getenv("HINDSIGHT_TIMEOUT", "2.0"))
    hindsight_max_tokens: int = int(os.getenv("HINDSIGHT_MAX_TOKENS", "2048"))
    
    # Feature flags & fallbacks
    enable_memory: bool = os.getenv("ENABLE_MEMORY", "true").lower() in ("true", "1", "yes")
    enable_security_agent: bool = os.getenv("ENABLE_SECURITY_AGENT", "true").lower() in ("true", "1", "yes")
    hindsight_async_retain: bool = os.getenv("HINDSIGHT_ASYNC_RETAIN", "false").lower() in ("true", "1", "yes")
    hindsight_circuit_breaker_threshold: int = int(os.getenv("HINDSIGHT_CIRCUIT_BREAKER_THRESHOLD", "2"))
    hindsight_circuit_breaker_timeout: float = float(os.getenv("HINDSIGHT_CIRCUIT_BREAKER_TIMEOUT", "10.0"))
    
    # Security Agent LLM configuration (optional)
    llm_provider: str = os.getenv("SECURITY_AGENT_PROVIDER", "heuristic") # "openai", "gemini", "heuristic"
    llm_api_key: Optional[str] = os.getenv("OPENAI_API_KEY", os.getenv("GEMINI_API_KEY", None))
    llm_model: str = os.getenv("SECURITY_AGENT_MODEL", "gpt-4o-mini")
    agent_timeout: float = float(os.getenv("SECURITY_AGENT_TIMEOUT", "2.0"))

    # Challenge and Model Settings
    model_path: str = os.getenv(
        "MODEL_PATH",
        os.path.join(os.path.dirname(__file__), "captcha_model.pkl")
    )
    challenge_timeout_seconds: int = int(os.getenv("CHALLENGE_TIMEOUT_SECONDS", "300"))

    # CORS Configuration (comma-separated origins or '*' for local development)
    cors_allowed_origins: list[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ALLOWED_ORIGINS", "*").split(",")
        if origin.strip()
    ]

config = AppConfig()
