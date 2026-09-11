"""
Configuration settings for Lunar Correspondence AI
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
STORAGE_DIR = BASE_DIR / "storage" / "uploads"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
BENCHMARK_DIR = BASE_DIR / "data" / "benchmark_pairs"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

SECRET_KEY = os.environ.get("LUNAR_SECRET_KEY", "lunar-secret-telemetry-key-chandrayaan2-scientific")
MAX_CONTENT_LENGTH = 35 * 1024 * 1024  # 35 MB max upload
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 5050))
