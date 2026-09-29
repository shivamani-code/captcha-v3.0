import os
import sys
import time
import json
import threading
import pytest
import uvicorn
from fastapi.testclient import TestClient

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from mock_hindsight_server import mock_hindsight_app, STORAGE_FILE
from app import app, challenges
from hindsight_memory import hindsight_service

_server_started = False
_server_thread = None

def _is_port_in_use(host="127.0.0.1", port=8888) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex((host, port)) == 0

@pytest.fixture(scope="session", autouse=True)
def start_hindsight_service():
    global _server_started, _server_thread
    if not _server_started and not _is_port_in_use("127.0.0.1", 8888):
        config = uvicorn.Config(
            mock_hindsight_app,
            host="127.0.0.1",
            port=8888,
            log_level="error",
        )
        server = uvicorn.Server(config)
        _server_thread = threading.Thread(target=server.run, daemon=True)
        _server_thread.start()
        time.sleep(0.8)
        _server_started = True
    
    # Re-init client to ensure connection
    hindsight_service._init_client()
    yield

@pytest.fixture(autouse=True)
def clean_storage():
    """Ensure clean memory bank state for each test."""
    if os.path.exists(STORAGE_FILE):
        try:
            os.remove(STORAGE_FILE)
        except Exception:
            pass
    challenges.clear()
    yield
    if os.path.exists(STORAGE_FILE):
        try:
            os.remove(STORAGE_FILE)
        except Exception:
            pass
    challenges.clear()

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def sample_human_features():
    return {
        "avg_mouse_speed": 340.5,
        "mouse_path_entropy": 0.65,
        "click_delay": 1.2,
        "task_completion_time": 1.8,
        "idle_time": 0.2,
        "micro_jitter_variance": 45.0,
        "acceleration_curve": 1200.0,
        "curvature_variance": 0.04,
        "overshoot_correction_ratio": 0.08,
        "timing_entropy": 0.75,
    }

@pytest.fixture
def sample_bot_features():
    return {
        "avg_mouse_speed": 2200.0,
        "mouse_path_entropy": 0.02,
        "click_delay": 0.05,
        "task_completion_time": 0.15,
        "idle_time": 0.01,
        "micro_jitter_variance": 0.05,
        "acceleration_curve": 20.0,
        "curvature_variance": 0.0001,
        "overshoot_correction_ratio": 0.001,
        "timing_entropy": 0.03,
    }
