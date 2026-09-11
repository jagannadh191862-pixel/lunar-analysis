"""
Vercel Serverless Entry Point — Lunar Correspondence AI
This file is the single Python handler Vercel invokes for all /api/* routes.
It wraps the existing Flask app and serves benchmark images directly.
"""

import sys
import os
from pathlib import Path

# Make backend importable from the project root
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Signal to backend modules that we are running on Vercel
os.environ.setdefault("VERCEL_ENV", "1")

from backend.app import create_app

# Create the Flask app — Vercel calls `app` as the WSGI handler
app = create_app()
