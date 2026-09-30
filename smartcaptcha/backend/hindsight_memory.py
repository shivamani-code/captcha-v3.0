import logging
import time
import asyncio
from typing import List, Optional, Tuple, Dict, Any

import hindsight_client.hindsight_client as hc
from hindsight_client import Hindsight, RecallResponse, RetainResponse, RecallResult
from config import config
from memory_schema import SecurityExperience, RecalledMemoryItem

# Patch hindsight_client synchronous runner to ensure aiohttp TimerContext has an active task in Python 3.14
def _safe_run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(lambda: asyncio.run(coro)).result()

    task = loop.create_task(coro)
    return loop.run_until_complete(task)

hc._run_async = _safe_run_async

logger = logging.getLogger("swipecha.hindsight")
logging.basicConfig(level=logging.INFO)

class CircuitBreaker:
    """
    In-memory circuit breaker to eliminate sequential outage latency.
    Fast-bypasses Hindsight calls in 0ms when Hindsight is known to be offline.
    """
    def __init__(self, failure_threshold: int = 2, recovery_timeout: float = 10.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def is_open(self) -> bool:
        if self.state == "OPEN":
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker entered HALF_OPEN state; testing Hindsight recovery.")
                return False
            return True
        return False

    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(
                f"Hindsight circuit breaker tripped to OPEN after {self.failure_count} consecutive failures. "
                f"Fast-bypassing calls for {self.recovery_timeout}s."
            )

    def trip(self):
        """Force the circuit breaker to OPEN state (for testing / manual trip)."""
        self.failure_count = self.failure_threshold
        self.last_failure_time = time.time()
        self.state = "OPEN"

    def reset(self):
        """Reset circuit breaker to clean CLOSED state."""
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"

class HindsightMemoryService:
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        bank_id: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        self.base_url = base_url or config.hindsight_api_key and config.hindsight_api_url or (base_url or config.hindsight_api_url)
        self.api_key = api_key or config.hindsight_api_key
        self.default_bank_id = bank_id or config.hindsight_default_bank_id
        self.timeout = timeout if timeout is not None else config.hindsight_timeout
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=config.hindsight_circuit_breaker_threshold,
            recovery_timeout=config.hindsight_circuit_breaker_timeout,
        )
        self._ensure_local_backend_if_configured()

    def _ensure_local_backend_if_configured(self):
        if not config.enable_memory:
            return
        normalized_url = (self.base_url or "").rstrip("/").lower()
        if normalized_url in ("http://127.0.0.1:8888", "http://localhost:8888"):
            try:
                from mock_hindsight_server import ensure_mock_server_running
                ensure_mock_server_running(host="127.0.0.1", port=8888)
            except Exception as e:
                logger.debug(f"Could not auto-start local Hindsight server: {e}")

    def _init_client(self):
        """Backwards compatibility hook; client is managed per-call."""
        self._ensure_local_backend_if_configured()
        self.circuit_breaker.reset()

    def _get_client(self) -> Optional[Hindsight]:
        self._ensure_local_backend_if_configured()
        try:
            return Hindsight(
                base_url=self.base_url,
                api_key=self.api_key,
                timeout=self.timeout,
            )
        except Exception as e:
            logger.warning(f"Failed to instantiate Hindsight client: {e}")
            return None

    def check_health(self) -> Tuple[bool, str]:
        """
        Validates connectivity to the Hindsight API without leaking keys.
        Returns (is_healthy, status_message).
        """
        if not config.enable_memory:
            return False, "disabled"

        if self.circuit_breaker.is_open():
            return False, "circuit_open_unavailable"

        client = self._get_client()
        if not client:
            self.circuit_breaker.record_failure()
            return False, "client_init_failed"

        try:
            version_info = client.get_version()
            api_version = getattr(version_info, "api_version", "unknown")
            self.circuit_breaker.record_success()
            return True, f"connected (API {api_version})"
        except Exception as e:
            logger.debug(f"Hindsight health check failed: {e}")
            self.circuit_breaker.record_failure()
            return False, "unavailable"
        finally:
            try:
                client.close()
            except Exception:
                pass

    def build_recall_query(self, behavior: Dict[str, float], ml_prediction: str, hard_rule: str) -> str:
        """
        Constructs a concise, security-relevant semantic recall query.
        Does not query generic text; focuses on dynamic gesture signatures.
        """
        speed = behavior.get("avg_mouse_speed", 0.0)
        entropy = behavior.get("mouse_path_entropy", 0.0)
        dur = behavior.get("task_completion_time", 0.0)
        jitter = behavior.get("micro_jitter_variance", 0.0)
        timing_h = behavior.get("timing_entropy", 0.0)

        return (
            f"SwipeCHA security experience for interaction: speed={speed:.1f}px/s, "
            f"path_entropy={entropy:.3f}, completion_time={dur:.2f}s, "
            f"jitter_variance={jitter:.2f}, timing_entropy={timing_h:.3f}, "
            f"ML={ml_prediction}, hard_rule={hard_rule}."
        )

    def recall(
        self,
        query: str,
        bank_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        max_tokens: Optional[int] = None,
    ) -> Tuple[List[RecalledMemoryItem], str]:
        """
        Retrieves relevant prior security experiences.
        Returns (normalized_memories, memory_status).
        Falls back safely without throwing unhandled exceptions.
        Fast-bypasses in 0ms when circuit breaker is OPEN.
        """
        if not config.enable_memory:
            return [], "disabled"

        if self.circuit_breaker.is_open():
            logger.debug("Hindsight circuit breaker OPEN; fast-bypassing recall.")
            return [], "unavailable"

        target_bank = bank_id or self.default_bank_id
        effective_tags = tags or ["swipecha", "security"]
        tokens = max_tokens or config.hindsight_max_tokens

        client = self._get_client()
        if not client:
            self.circuit_breaker.record_failure()
            return [], "unavailable"

        try:
            resp: RecallResponse = client.recall(
                bank_id=target_bank,
                query=query,
                tags=effective_tags,
                max_tokens=tokens,
                budget="mid",
            )
            raw_results = getattr(resp, "results", []) or []
            normalized: List[RecalledMemoryItem] = []

            for r in raw_results:
                mem_id = getattr(r, "id", "")
                text = getattr(r, "text", "")
                r_tags = getattr(r, "tags", []) or []
                metadata = getattr(r, "metadata", {}) or {}
                occurred_at = getattr(r, "occurred_start", None)

                # Safely extract scores if available
                scores = getattr(r, "scores", None)
                score = None
                if scores and hasattr(scores, "final"):
                    score = float(scores.final)
                elif isinstance(scores, dict):
                    score = float(scores.get("final", 0.0))

                normalized.append(
                    RecalledMemoryItem(
                        id=str(mem_id),
                        text=str(text),
                        tags=list(r_tags),
                        score=score,
                        metadata=dict(metadata) if isinstance(metadata, dict) else {},
                        occurred_at=str(occurred_at) if occurred_at else None,
                    )
                )

            self.circuit_breaker.record_success()
            return normalized, "available"

        except TimeoutError:
            self.circuit_breaker.record_failure()
            logger.warning("Hindsight recall timed out; proceeding with baseline fallback.")
            return [], "unavailable"
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.warning(f"Hindsight recall error: {e}; proceeding with baseline fallback.")
            return [], "error"
        finally:
            try:
                client.close()
            except Exception:
                pass

    def retain(
        self,
        experience: SecurityExperience,
        bank_id: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Retains a distilled security experience.
        Returns (success, retain_status).
        Safely isolated to the specified bank_id.
        Fast-bypasses in 0ms when circuit breaker is OPEN.
        """
        if not config.enable_memory:
            return False, "skipped"

        if self.circuit_breaker.is_open():
            logger.debug("Hindsight circuit breaker OPEN; fast-bypassing retain.")
            return False, "unavailable"

        target_bank = bank_id or experience.bank_id or self.default_bank_id

        client = self._get_client()
        if not client:
            self.circuit_breaker.record_failure()
            return False, "unavailable"

        content = experience.to_natural_language()
        tags = ["swipecha", "security", experience.final_outcome.lower()]
        metadata = {
            "source": experience.source,
            "final_outcome": experience.final_outcome,
            "ml_prediction": experience.ml_prediction,
            "gate": experience.gate,
            "risk_level": experience.risk_level,
        }

        try:
            resp: RetainResponse = client.retain(
                bank_id=target_bank,
                content=content,
                metadata=metadata,
                tags=tags,
                retain_async=False,
            )
            success = bool(getattr(resp, "success", True))
            if success:
                self.circuit_breaker.record_success()
            else:
                self.circuit_breaker.record_failure()
            return success, "retained" if success else "failed"

        except TimeoutError:
            self.circuit_breaker.record_failure()
            logger.warning("Hindsight retain timed out; verification completes safely.")
            return False, "timeout"
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.warning(f"Hindsight retain error: {e}; verification completes safely.")
            return False, "failed"
        finally:
            try:
                client.close()
            except Exception:
                pass

hindsight_service = HindsightMemoryService()
