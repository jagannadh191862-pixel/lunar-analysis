"""
Analysis Routes for Lunar Correspondence AI
Handles image upload, multi-sensor validation, analysis execution,
real-time metrics generation, and history archives.
"""

import os
import uuid
import time
from pathlib import Path
from flask import Blueprint, request, jsonify, session
from werkzeug.utils import secure_filename
import cv2

from backend.config import STORAGE_DIR, ALLOWED_EXTENSIONS
from backend.db.database import (
    insert_image_pair,
    get_image_pair_by_id,
    create_analysis,
    save_analysis_results,
    update_analysis_status,
    get_analysis_full_details,
    get_user_history
)
from backend.engine.vision_engine import vision_engine

analysis_bp = Blueprint("analysis", __name__, url_prefix="/api/analysis")

def is_allowed_file(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS

@analysis_bp.route("/upload", methods=["POST"])
def upload_image_pair():
    """
    Accepts two user-uploaded planetary images (Reference Image A and Target Image B),
    validates format, dimensions, sensor parameters, and creates a new image_pair record.
    """
    if "ref_image" not in request.files or "tgt_image" not in request.files:
        return jsonify({
            "error": "Analysis could not be completed",
            "message": "Both Reference Image (Sensor A) and Target Image (Sensor B) are required for correspondence analysis."
        }), 400

    ref_file = request.files["ref_image"]
    tgt_file = request.files["tgt_image"]

    if not ref_file.filename or not tgt_file.filename:
        return jsonify({
            "error": "Analysis could not be completed",
            "message": "Selected files must have valid filenames."
        }), 400

    if not is_allowed_file(ref_file.filename) or not is_allowed_file(tgt_file.filename):
        return jsonify({
            "error": "Analysis could not be completed",
            "message": "Unsupported file format. Please upload standard planetary imaging formats (.png, .jpg, .jpeg, .tif, .tiff)."
        }), 400

    pair_name = request.form.get("pair_name", "").strip() or f"Observation {time.strftime('%Y-%m-%d %H:%M:%S')}"
    target_region = request.form.get("target_region", "Lunar Surface").strip()
    
    ref_sensor = request.form.get("ref_sensor", "Chandrayaan-2 TMC-2").strip()
    ref_gsd = float(request.form.get("ref_gsd", 5.0))
    ref_sun_el = float(request.form.get("ref_sun_elevation", 15.0))

    tgt_sensor = request.form.get("tgt_sensor", "Chandrayaan-2 OHRC").strip()
    tgt_gsd = float(request.form.get("tgt_gsd", 0.32))
    tgt_sun_el = float(request.form.get("tgt_sun_elevation", 15.0))

    center_lat = float(request.form.get("center_latitude", 0.0))
    center_lon = float(request.form.get("center_longitude", 0.0))

    # Secure unique file saving
    ref_ext = Path(ref_file.filename).suffix.lower()
    tgt_ext = Path(tgt_file.filename).suffix.lower()
    ref_save_name = f"ref_{uuid.uuid4().hex[:12]}{ref_ext}"
    tgt_save_name = f"tgt_{uuid.uuid4().hex[:12]}{tgt_ext}"

    ref_save_path = STORAGE_DIR / ref_save_name
    tgt_save_path = STORAGE_DIR / tgt_save_name

    ref_file.save(str(ref_save_path))
    tgt_file.save(str(tgt_save_path))

    # Sanity validation on decoded image
    img_ref = cv2.imread(str(ref_save_path), cv2.IMREAD_UNCHANGED)
    img_tgt = cv2.imread(str(tgt_save_path), cv2.IMREAD_UNCHANGED)

    if img_ref is None or img_tgt is None:
        # Cleanup invalid files
        if ref_save_path.exists(): ref_save_path.unlink()
        if tgt_save_path.exists(): tgt_save_path.unlink()
        return jsonify({
            "error": "Analysis could not be completed",
            "message": "The uploaded images could not be decoded. Please verify the integrity of the image data and try again."
        }), 400

    h_ref, w_ref = img_ref.shape[:2]
    h_tgt, w_tgt = img_tgt.shape[:2]

    if min(h_ref, w_ref, h_tgt, w_tgt) < 64:
        if ref_save_path.exists(): ref_save_path.unlink()
        if tgt_save_path.exists(): tgt_save_path.unlink()
        return jsonify({
            "error": "Analysis could not be completed",
            "message": "Image dimensions are too small (< 64px). Feature extraction requires sufficient spatial resolution."
        }), 400

    user_id = session.get("user_id")
    pair_id = insert_image_pair(
        pair_name=pair_name,
        ref_image_path=str(ref_save_path),
        ref_sensor=ref_sensor,
        ref_gsd=ref_gsd,
        tgt_image_path=str(tgt_save_path),
        tgt_sensor=tgt_sensor,
        tgt_gsd=tgt_gsd,
        user_id=user_id,
        is_demo=0,
        target_region=target_region,
        center_lat=center_lat,
        center_lon=center_lon,
        ref_sun_elevation=ref_sun_el,
        tgt_sun_elevation=tgt_sun_el
    )

    return jsonify({
        "message": "Images validated and registered successfully.",
        "pair_id": pair_id,
        "ref_image_url": f"/storage/uploads/{ref_save_name}",
        "tgt_image_url": f"/storage/uploads/{tgt_save_name}",
        "metadata": {
            "ref_dimensions": f"{w_ref}x{h_ref}",
            "tgt_dimensions": f"{w_tgt}x{h_tgt}",
            "ref_sensor": ref_sensor,
            "tgt_sensor": tgt_sensor
        }
    }), 201

@analysis_bp.route("/run", methods=["POST"])
def run_analysis():
    """
    Executes the multi-stage planetary correspondence analysis pipeline.
    Stages:
      1. Image validation & radiometric normalization (CLAHE)
      2. Multi-scale feature extraction (ORB/SIFT/AKAZE)
      3. Cross-descriptor matching with Lowe's ratio test
      4. RANSAC geometric verification & reprojection residual calculation
      5. Metrics persistence & vector results generation
    """
    data = request.get_json() or {}
    pair_id = data.get("pair_id")
    if not pair_id:
        return jsonify({
            "error": "Analysis could not be completed",
            "message": "Missing required parameter 'pair_id'."
        }), 400

    pair = get_image_pair_by_id(int(pair_id))
    if not pair:
        return jsonify({
            "error": "Analysis could not be completed",
            "message": f"Image pair ID {pair_id} was not found in active telemetry records."
        }), 404

    detector_type = str(data.get("detector_type", "ORB")).upper()
    if detector_type not in ["ORB", "SIFT", "AKAZE"]:
        detector_type = "ORB"

    model_type = str(data.get("model_type", "HOMOGRAPHY")).upper()
    if model_type not in ["HOMOGRAPHY", "AFFINE"]:
        model_type = "HOMOGRAPHY"

    try:
        ransac_threshold = float(data.get("ransac_threshold", 2.5))
    except (ValueError, TypeError):
        ransac_threshold = 2.5

    try:
        ratio_threshold = float(data.get("ratio_threshold", 0.75))
    except (ValueError, TypeError):
        ratio_threshold = 0.75

    clahe_enabled = bool(data.get("clahe_enabled", True))

    user_id = session.get("user_id")

    # Register analysis record in DB
    analysis_id = create_analysis(
        pair_id=pair["id"],
        user_id=user_id,
        detector_type=detector_type,
        model_type=model_type,
        ransac_threshold=ransac_threshold,
        ratio_threshold=ratio_threshold,
        clahe_enabled=1 if clahe_enabled else 0
    )

    ref_path = pair["ref_image_path"]
    tgt_path = pair["tgt_image_path"]

    # Verify disk files exist
    if not os.path.exists(ref_path) or not os.path.exists(tgt_path):
        update_analysis_status(analysis_id, "FAILED", error_message="Image files missing from disk storage.")
        return jsonify({
            "error": "Analysis could not be completed",
            "message": "The processing service was unable to locate the source images on disk. Please re-upload or select a benchmark dataset."
        }), 500

    try:
        results = vision_engine.analyze_pair(
            ref_image_path=ref_path,
            tgt_image_path=tgt_path,
            detector_type=detector_type,
            model_type=model_type,
            ransac_threshold=ransac_threshold,
            ratio_threshold=ratio_threshold,
            clahe_enabled=clahe_enabled
        )

        save_analysis_results(
            analysis_id=analysis_id,
            metrics_data=results["metrics"],
            matches=results["matches"]
        )

        full_analysis = get_analysis_full_details(analysis_id)
        
        # Attach convenient web URLs for images
        if pair["is_demo"]:
            full_analysis["ref_image_url"] = f"/data/benchmark_pairs/{Path(pair['ref_image_path']).name}"
            full_analysis["tgt_image_url"] = f"/data/benchmark_pairs/{Path(pair['tgt_image_path']).name}"
        else:
            full_analysis["ref_image_url"] = f"/storage/uploads/{Path(pair['ref_image_path']).name}"
            full_analysis["tgt_image_url"] = f"/storage/uploads/{Path(pair['tgt_image_path']).name}"

        return jsonify({
            "message": "Planetary correspondence analysis completed successfully.",
            "analysis": full_analysis
        }), 200

    except Exception as e:
        update_analysis_status(analysis_id, "FAILED", error_message=str(e))
        return jsonify({
            "error": "Analysis could not be completed",
            "message": f"Scientific vision engine encountered an exception: {str(e)}. Please review the image inputs or adjust algorithmic parameters."
        }), 500

@analysis_bp.route("/<int:analysis_id>", methods=["GET"])
def get_analysis(analysis_id: int):
    """Retrieves full analysis record, metrics, and keypoint matches."""
    analysis = get_analysis_full_details(analysis_id)
    if not analysis:
        return jsonify({
            "error": "Analysis record not found",
            "message": f"No analysis record exists with ID {analysis_id}."
        }), 404

    # Format web URLs
    is_demo = "/data/benchmark_pairs/" in analysis["ref_image_path"] or "ch2_" in analysis["ref_image_path"]
    if is_demo:
        analysis["ref_image_url"] = f"/data/benchmark_pairs/{Path(analysis['ref_image_path']).name}"
        analysis["tgt_image_url"] = f"/data/benchmark_pairs/{Path(analysis['tgt_image_path']).name}"
    else:
        analysis["ref_image_url"] = f"/storage/uploads/{Path(analysis['ref_image_path']).name}"
        analysis["tgt_image_url"] = f"/storage/uploads/{Path(analysis['tgt_image_path']).name}"

    return jsonify({"analysis": analysis}), 200

@analysis_bp.route("/history", methods=["GET"])
def get_history():
    """Retrieves past planetary analysis runs."""
    user_id = session.get("user_id")
    limit = int(request.args.get("limit", 20))
    history = get_user_history(user_id=user_id, limit=limit)
    return jsonify({"history": history}), 200
