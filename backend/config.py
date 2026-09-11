"""
Configuration settings for Lunar Correspondence AI
Vercel-compatible: uses /tmp for uploads on serverless (read-only filesystem).
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# Benchmark images are bundled with code — always readable
BENCHMARK_DIR = BASE_DIR / "data" / "benchmark_pairs"

# Frontend: served as static on Vercel, or from /frontend locally
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# Uploads: /tmp on Vercel (ephemeral), local storage/ in dev
if os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"):
    STORAGE_DIR = Path("/tmp/uploads")
else:
    STORAGE_DIR = BASE_DIR / "storage" / "uploads"

STORAGE_DIR.mkdir(parents=True, exist_ok=True)

SECRET_KEY = os.environ.get("LUNAR_SECRET_KEY", "lunar-secret-telemetry-key-chandrayaan2-scientific")
MAX_CONTENT_LENGTH = 35 * 1024 * 1024  # 35 MB max upload
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}

HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 5050))
