import os
import sys

# Ensure smartcaptcha/backend is in sys.path
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "smartcaptcha", "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app import app
