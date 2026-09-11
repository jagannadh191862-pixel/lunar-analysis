"""
Demo & Benchmark Routes for Lunar Correspondence AI
Serves verified benchmark datasets (Chandrayaan-2 TMC-2 / OHRC, LROC Shackleton, Serenitatis).
"""

import json
from pathlib import Path
from flask import Blueprint, jsonify, current_app
from backend.config import BASE_DIR, BENCHMARK_DIR
from backend.db.database import insert_image_pair, get_demo_pairs, get_connection

demo_bp = Blueprint("demo", __name__, url_prefix="/api/demo")

def ensure_benchmark_database_records():
    """Seeds the database with benchmark image pairs if not already present."""
    metadata_file = BASE_DIR / "data" / "metadata.json"
    if not metadata_file.exists():
        return

    with open(metadata_file, "r", encoding="utf-8") as f:
        benchmarks = json.load(f)

    conn = get_connection()
    try:
        cursor = conn.cursor()
        for b in benchmarks:
            cursor.execute("SELECT id FROM image_pairs WHERE pair_name = ? AND is_demo = 1", (b["pair_name"],))
            row = cursor.fetchone()
            if not row:
                ref_path = str(BENCHMARK_DIR / b["ref_filename"])
                tgt_path = str(BENCHMARK_DIR / b["tgt_filename"])
                insert_image_pair(
                    pair_name=b["pair_name"],
                    ref_image_path=ref_path,
                    ref_sensor=b["ref_sensor"],
                    ref_gsd=b["ref_gsd"],
                    tgt_image_path=tgt_path,
                    tgt_sensor=b["tgt_sensor"],
                    tgt_gsd=b["tgt_gsd"],
                    user_id=None,
                    is_demo=1,
                    target_region=b["target_region"],
                    center_lat=b["center_latitude"],
                    center_lon=b["center_longitude"],
                    ref_sun_elevation=b["ref_sun_elevation"],
                    tgt_sun_elevation=b["tgt_sun_elevation"]
                )
    finally:
        conn.close()

@demo_bp.route("/pairs", methods=["GET"])
def list_demo_pairs():
    """Returns curated benchmark datasets with scientific ground-truth metadata."""
    ensure_benchmark_database_records()
    pairs = get_demo_pairs()
    
    metadata_file = BASE_DIR / "data" / "metadata.json"
    desc_map = {}
    if metadata_file.exists():
        with open(metadata_file, "r", encoding="utf-8") as f:
            for item in json.load(f):
                desc_map[item["pair_name"]] = item.get("description", "")

    results = []
    for p in pairs:
        pair_data = dict(p)
        pair_data["description"] = desc_map.get(p["pair_name"], "Verified Lunar Benchmark Observation.")
        # Web URLs for the benchmark images
        pair_data["ref_image_url"] = f"/data/benchmark_pairs/{Path(p['ref_image_path']).name}"
        pair_data["tgt_image_url"] = f"/data/benchmark_pairs/{Path(p['tgt_image_path']).name}"
        results.append(pair_data)

    return jsonify({"benchmark_pairs": results}), 200

@demo_bp.route("/load/<int:pair_id>", methods=["GET"])
def load_benchmark_pair(pair_id: int):
    """Fetches details for a specific benchmark pair."""
    ensure_benchmark_database_records()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM image_pairs WHERE id = ?", (pair_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Benchmark dataset not found."}), 404
        
        data = dict(row)
        data["ref_image_url"] = f"/data/benchmark_pairs/{Path(data['ref_image_path']).name}"
        data["tgt_image_url"] = f"/data/benchmark_pairs/{Path(data['tgt_image_path']).name}"
        return jsonify({"pair": data}), 200
    finally:
        conn.close()
