"""
Lunar Correspondence AI - Scientific Web Application Server
Production-grade Flask server serving REST APIs and static aerospace interface.
Vercel-compatible: benchmark images and uploads served via Flask routes.
"""

import os
import sys
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, send_file
from flask_cors import CORS

# Ensure backend root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import (
    SECRET_KEY,
    MAX_CONTENT_LENGTH,
    STORAGE_DIR,
    BENCHMARK_DIR,
    FRONTEND_DIR,
    HOST,
    PORT
)
from backend.db.database import init_db
from backend.api.routes_auth import auth_bp
from backend.api.routes_demo import demo_bp, ensure_benchmark_database_records
from backend.api.routes_analysis import analysis_bp
from backend.api.routes_export import export_bp

_IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"))

def create_app() -> Flask:
    # On Vercel, static files are served from /public by Vercel CDN,
    # so we don't need Flask to serve them — only the API matters.
    app = Flask(__name__, static_folder=None)
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

    # Enable CORS for scientific client integrations
    CORS(app, supports_credentials=True)

    # Initialize Database & Seed Benchmarks
    try:
        init_db()
        ensure_benchmark_database_records()
    except Exception as e:
        print(f"[WARN] DB init warning (non-fatal on cold start): {e}")

    # Register API Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(demo_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(export_bp)

    # Serve benchmark images (needed on Vercel where /backend/data is bundled)
    @app.route("/data/benchmark_pairs/<path:filename>")
    def serve_benchmark_image(filename):
        safe = Path(filename).name  # prevent path traversal
        fp = BENCHMARK_DIR / safe
        if not fp.exists():
            return jsonify({"error": "Benchmark image not found"}), 404
        return send_file(str(fp))

    # Serve user-uploaded images (stored in /tmp on Vercel)
    @app.route("/storage/uploads/<path:filename>")
    def serve_uploaded_image(filename):
        safe = Path(filename).name
        fp = STORAGE_DIR / safe
        if not fp.exists():
            return jsonify({"error": "Upload not found"}), 404
        return send_file(str(fp))

    # Serve frontend index.html for non-API, non-Vercel environments
    if not _IS_VERCEL:
        @app.route("/")
        def serve_index():
            return send_from_directory(str(FRONTEND_DIR), "index.html")

        @app.route("/<path:filename>")
        def serve_static(filename):
            fp = FRONTEND_DIR / filename
            if fp.is_file():
                return send_from_directory(str(FRONTEND_DIR), filename)
            return send_from_directory(str(FRONTEND_DIR), "index.html")

    # Professional scientific error handlers
    @app.errorhandler(400)
    def bad_request_error(e):
        return jsonify({
            "error": "Analysis could not be completed",
            "message": str(e.description) if hasattr(e, "description") else "The request parameters are invalid.",
            "code": "BAD_REQUEST"
        }), 400

    @app.errorhandler(404)
    def not_found_error(e):
        return jsonify({
            "error": "Telemetry resource not found",
            "message": "The requested planetary record or endpoint does not exist.",
            "code": "NOT_FOUND"
        }), 404

    @app.errorhandler(413)
    def file_too_large_error(e):
        return jsonify({
            "error": "Analysis could not be completed",
            "message": "The uploaded telemetry image exceeds the maximum permitted size limit (35 MB).",
            "code": "PAYLOAD_TOO_LARGE"
        }), 413

    @app.errorhandler(500)
    def internal_server_error(e):
        return jsonify({
            "error": "Analysis could not be completed",
            "message": "The processing service was unable to analyze the request. Please verify the image format and try again, or use Demo Mode.",
            "code": "INTERNAL_PROCESSING_ERROR"
        }), 500

    return app

app = create_app()

if __name__ == "__main__":
    print(f"============================================================")
    print(f"   LUNAR CORRESPONDENCE AI — Operational Scientific Server")
    print(f"   Listening on http://localhost:{PORT}")
    print(f"============================================================")
    app.run(host=HOST, port=PORT, debug=True)
