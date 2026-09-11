"""
Export Routes for Lunar Correspondence AI
Exports scientific data products: CSV keypoint records, JSON mission reports,
and high-resolution annotated composite correspondence maps.
"""

import io
import csv
import json
from pathlib import Path
from flask import Blueprint, send_file, jsonify, make_response
import cv2
import numpy as np

from backend.db.database import get_analysis_full_details

export_bp = Blueprint("export", __name__, url_prefix="/api/export")

@export_bp.route("/<int:analysis_id>/csv", methods=["GET"])
def export_csv(analysis_id: int):
    """Exports matched keypoint coordinates and residuals as a scientific CSV."""
    analysis = get_analysis_full_details(analysis_id)
    if not analysis:
        return jsonify({"error": "Analysis record not found"}), 404

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "match_index",
        "ref_x_px",
        "ref_y_px",
        "tgt_x_px",
        "tgt_y_px",
        "confidence_score",
        "is_verified_inlier",
        "reprojection_residual_px"
    ])

    for m in analysis.get("matches", []):
        writer.writerow([
            m["match_index"],
            m["ref_x"],
            m["ref_y"],
            m["tgt_x"],
            m["tgt_y"],
            m["confidence"],
            m["is_inlier"],
            m["residual_error"]
        ])

    output.seek(0)
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=lunar_correspondence_analysis_{analysis_id}.csv"
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    return response

@export_bp.route("/<int:analysis_id>/json", methods=["GET"])
def export_json(analysis_id: int):
    """Exports full scientific metadata, transformation matrix, and keypoints as JSON."""
    analysis = get_analysis_full_details(analysis_id)
    if not analysis:
        return jsonify({"error": "Analysis record not found"}), 404

    # Structure scientific laboratory report
    report = {
        "mission_title": "LUNAR CORRESPONDENCE AI - Planetary Feature Analysis Report",
        "analysis_id": analysis["id"],
        "observation_target": analysis["pair_name"],
        "target_region": analysis["target_region"],
        "coordinates": {
            "latitude": analysis["center_latitude"],
            "longitude": analysis["center_longitude"]
        },
        "instrumentation": {
            "reference_sensor": {
                "instrument": analysis["ref_sensor"],
                "ground_sampling_distance_m": analysis["ref_gsd"],
                "sun_elevation_deg": analysis["ref_sun_elevation"]
            },
            "target_sensor": {
                "instrument": analysis["tgt_sensor"],
                "ground_sampling_distance_m": analysis["tgt_gsd"],
                "sun_elevation_deg": analysis["tgt_sun_elevation"]
            }
        },
        "algorithmic_parameters": {
            "feature_detector": analysis["detector_type"],
            "geometric_model": analysis["model_type"],
            "ransac_threshold_px": analysis["ransac_threshold"],
            "ratio_test_threshold": analysis["ratio_threshold"],
            "clahe_shadow_equalization": bool(analysis["clahe_enabled"])
        },
        "scientific_metrics": analysis["metrics"],
        "execution_telemetry": {
            "total_latency_ms": analysis["total_time_ms"],
            "status": analysis["status"],
            "timestamp": analysis["created_at"]
        },
        "keypoint_matches_count": len(analysis.get("matches", [])),
        "keypoint_matches": analysis.get("matches", [])
    }

    response = make_response(json.dumps(report, indent=2))
    response.headers["Content-Disposition"] = f"attachment; filename=lunar_report_analysis_{analysis_id}.json"
    response.headers["Content-Type"] = "application/json"
    return response

@export_bp.route("/<int:analysis_id>/composite", methods=["GET"])
def export_composite_image(analysis_id: int):
    """Generates a high-resolution annotated composite image with correspondence vectors."""
    analysis = get_analysis_full_details(analysis_id)
    if not analysis:
        return jsonify({"error": "Analysis record not found"}), 404

    ref_img = cv2.imread(analysis["ref_image_path"])
    tgt_img = cv2.imread(analysis["tgt_image_path"])
    if ref_img is None or tgt_img is None:
        return jsonify({"error": "Underlying image data missing"}), 500

    h_a, w_a = ref_img.shape[:2]
    h_b, w_b = tgt_img.shape[:2]

    # Normalize heights
    max_h = max(h_a, h_b)
    if h_a != max_h:
        ref_img = cv2.resize(ref_img, (int(w_a * max_h / h_a), max_h))
    if h_b != max_h:
        tgt_img = cv2.resize(tgt_img, (int(w_b * max_h / h_b), max_h))

    w_a_scaled = ref_img.shape[1]
    w_b_scaled = tgt_img.shape[1]

    # Create composite canvas with center separator
    separator_w = 4
    composite = np.zeros((max_h, w_a_scaled + w_b_scaled + separator_w, 3), dtype=np.uint8)
    composite[:, :w_a_scaled] = ref_img
    composite[:, w_a_scaled:w_a_scaled + separator_w] = (30, 40, 55) # Divider
    composite[:, w_a_scaled + separator_w:] = tgt_img

    scale_a_x = w_a_scaled / float(w_a)
    scale_a_y = max_h / float(h_a)
    scale_b_x = w_b_scaled / float(w_b)
    scale_b_y = max_h / float(h_b)

    # Draw correspondence lines (inliers in emerald green, outliers in muted red)
    matches = analysis.get("matches", [])
    # Draw outliers first
    for m in matches:
        if not m["is_inlier"]:
            pt_a = (int(m["ref_x"] * scale_a_x), int(m["ref_y"] * scale_a_y))
            pt_b = (int(m["tgt_x"] * scale_b_x + w_a_scaled + separator_w), int(m["tgt_y"] * scale_b_y))
            cv2.line(composite, pt_a, pt_b, (40, 40, 180), 1, cv2.LINE_AA)

    # Draw inliers on top
    for m in matches:
        if m["is_inlier"]:
            pt_a = (int(m["ref_x"] * scale_a_x), int(m["ref_y"] * scale_a_y))
            pt_b = (int(m["tgt_x"] * scale_b_x + w_a_scaled + separator_w), int(m["tgt_y"] * scale_b_y))
            cv2.line(composite, pt_a, pt_b, (50, 210, 130), 1, cv2.LINE_AA)
            cv2.circle(composite, pt_a, 3, (50, 240, 130), -1, cv2.LINE_AA)
            cv2.circle(composite, pt_b, 3, (50, 240, 130), -1, cv2.LINE_AA)

    # Overlay metadata bar at top
    header_h = 44
    header_overlay = composite[:header_h, :].copy()
    cv2.rectangle(composite, (0, 0), (composite.shape[1], header_h), (12, 16, 24), -1)
    # Text annotation
    font = cv2.FONT_HERSHEY_SIMPLEX
    text = f"LUNAR CORRESPONDENCE AI | Inliers: {analysis['metrics']['verified_inliers_count']} / {analysis['metrics']['initial_matches_count']} ({analysis['metrics']['inlier_ratio_percent']}%) | RMSE: {analysis['metrics']['rmse_residual_px']}px"
    cv2.putText(composite, text, (18, 28), font, 0.6, (230, 240, 255), 1, cv2.LINE_AA)

    # Encode to PNG
    success, buffer = cv2.imencode(".png", composite)
    if not success:
        return jsonify({"error": "Failed to render composite"}), 500

    io_buf = io.BytesIO(buffer)
    io_buf.seek(0)
    return send_file(
        io_buf,
        mimetype="image/png",
        as_attachment=True,
        download_name=f"lunar_composite_analysis_{analysis_id}.png"
    )
