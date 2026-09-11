"""
Database Access Layer for Lunar Correspondence AI
Provides thread-safe SQLite operations, relational migrations,
password hashing with PBKDF2-HMAC-SHA256, and data access methods.
Vercel-compatible: uses /tmp for ephemeral writable storage on serverless.
"""

import os
import sqlite3
import hashlib
import secrets
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import shutil

_LOCAL_SCHEMA = Path(__file__).resolve().parent / "schema.sql"

# Vercel filesystem is read-only except /tmp
if os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"):
    DB_PATH = Path("/tmp/lunar_ai.db")
    SCHEMA_PATH = Path("/tmp/schema.sql")
    # Copy schema to /tmp so it's readable during cold start
    if _LOCAL_SCHEMA.exists() and not SCHEMA_PATH.exists():
        shutil.copy(str(_LOCAL_SCHEMA), str(SCHEMA_PATH))
else:
    DB_PATH = Path(__file__).resolve().parent / "lunar_ai.db"
    SCHEMA_PATH = _LOCAL_SCHEMA

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Initializes the database schema if not already present."""
    conn = get_connection()
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_script = f.read()
        conn.executescript(schema_script)
        conn.commit()
    finally:
        conn.close()

def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Hashes password with PBKDF2-HMAC-SHA256 and a 16-byte cryptographically secure salt."""
    if salt is None:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000
    )
    return key.hex(), salt

def verify_password(stored_hash: str, salt: str, provided_password: str) -> bool:
    """Verifies a user password against the stored PBKDF2 hash."""
    test_hash, _ = hash_password(provided_password, salt)
    return secrets.compare_digest(stored_hash, test_hash)

# User management
def create_user(username: str, email: str, password: str, role: str = "researcher", institution: str = "Planetary Remote Sensing Laboratory") -> Optional[int]:
    pwd_hash, salt = hash_password(password)
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO users (username, email, password_hash, salt, role, institution)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (username.strip(), email.strip().lower(), pwd_hash, salt, role, institution)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? OR email = ?", (username.strip(), username.strip().lower()))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, role, institution, created_at FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

# Image Pair management
def insert_image_pair(
    pair_name: str,
    ref_image_path: str,
    ref_sensor: str,
    ref_gsd: float,
    tgt_image_path: str,
    tgt_sensor: str,
    tgt_gsd: float,
    user_id: Optional[int] = None,
    is_demo: int = 0,
    target_region: str = "Lunar Surface",
    center_lat: float = 0.0,
    center_lon: float = 0.0,
    ref_sun_elevation: float = 15.0,
    tgt_sun_elevation: float = 15.0
) -> int:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO image_pairs 
               (user_id, pair_name, is_demo, target_region, center_latitude, center_longitude,
                ref_image_path, ref_sensor, ref_gsd, ref_sun_elevation,
                tgt_image_path, tgt_sensor, tgt_gsd, tgt_sun_elevation)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, pair_name, is_demo, target_region, center_lat, center_lon,
             ref_image_path, ref_sensor, ref_gsd, ref_sun_elevation,
             tgt_image_path, tgt_sensor, tgt_gsd, tgt_sun_elevation)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def get_image_pair_by_id(pair_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM image_pairs WHERE id = ?", (pair_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_demo_pairs() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM image_pairs WHERE is_demo = 1 ORDER BY id ASC")
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()

# Analysis & Metrics management
def create_analysis(
    pair_id: int,
    user_id: Optional[int] = None,
    detector_type: str = "ORB",
    model_type: str = "HOMOGRAPHY",
    ransac_threshold: float = 2.5,
    ratio_threshold: float = 0.75,
    clahe_enabled: int = 1
) -> int:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO analyses 
               (pair_id, user_id, detector_type, model_type, ransac_threshold, ratio_threshold, clahe_enabled, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'PROCESSING')""",
            (pair_id, user_id, detector_type, model_type, ransac_threshold, ratio_threshold, clahe_enabled)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def update_analysis_status(analysis_id: int, status: str, total_time_ms: float = 0.0, error_message: Optional[str] = None):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE analyses 
               SET status = ?, total_time_ms = ?, error_message = ? 
               WHERE id = ?""",
            (status, total_time_ms, error_message, analysis_id)
        )
        conn.commit()
    finally:
        conn.close()

def save_analysis_results(
    analysis_id: int,
    metrics_data: Dict[str, Any],
    matches: List[Dict[str, Any]]
):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Save metrics
        cursor.execute(
            """INSERT INTO metrics 
               (analysis_id, keypoints_ref_count, keypoints_tgt_count, initial_matches_count,
                verified_inliers_count, inlier_ratio_percent, rmse_residual_px,
                estimated_scale, estimated_rotation_deg, estimated_translation_x, estimated_translation_y,
                transform_matrix_json, preprocessing_ms, extraction_ms, matching_ms, verification_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                analysis_id,
                metrics_data["keypoints_ref_count"],
                metrics_data["keypoints_tgt_count"],
                metrics_data["initial_matches_count"],
                metrics_data["verified_inliers_count"],
                metrics_data["inlier_ratio_percent"],
                metrics_data["rmse_residual_px"],
                metrics_data["estimated_scale"],
                metrics_data["estimated_rotation_deg"],
                metrics_data["estimated_translation_x"],
                metrics_data["estimated_translation_y"],
                metrics_data["transform_matrix_json"],
                metrics_data.get("preprocessing_ms", 0.0),
                metrics_data.get("extraction_ms", 0.0),
                metrics_data.get("matching_ms", 0.0),
                metrics_data.get("verification_ms", 0.0)
            )
        )
        # Bulk save matches
        cursor.executemany(
            """INSERT INTO keypoint_matches 
               (analysis_id, match_index, ref_x, ref_y, tgt_x, tgt_y, confidence, is_inlier, residual_error)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    analysis_id,
                    idx,
                    m["ref_x"],
                    m["ref_y"],
                    m["tgt_x"],
                    m["tgt_y"],
                    m["confidence"],
                    1 if m.get("is_inlier", True) else 0,
                    m.get("residual_error", 0.0)
                )
                for idx, m in enumerate(matches)
            ]
        )
        cursor.execute(
            "UPDATE analyses SET status = 'COMPLETED', total_time_ms = ? WHERE id = ?",
            (metrics_data.get("total_time_ms", 0.0), analysis_id)
        )
        conn.commit()
    finally:
        conn.close()

def get_analysis_full_details(analysis_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT a.*, p.pair_name, p.ref_sensor, p.ref_gsd, p.tgt_sensor, p.tgt_gsd, 
                      p.target_region, p.center_latitude, p.center_longitude,
                      p.ref_sun_elevation, p.tgt_sun_elevation,
                      p.ref_image_path, p.tgt_image_path
               FROM analyses a
               JOIN image_pairs p ON a.pair_id = p.id
               WHERE a.id = ?""",
            (analysis_id,)
        )
        analysis_row = cursor.fetchone()
        if not analysis_row:
            return None
        
        analysis = dict(analysis_row)

        cursor.execute("SELECT * FROM metrics WHERE analysis_id = ?", (analysis_id,))
        metric_row = cursor.fetchone()
        analysis["metrics"] = dict(metric_row) if metric_row else None

        cursor.execute(
            """SELECT match_index, ref_x, ref_y, tgt_x, tgt_y, confidence, is_inlier, residual_error 
               FROM keypoint_matches 
               WHERE analysis_id = ? 
               ORDER BY is_inlier DESC, confidence DESC""",
            (analysis_id,)
        )
        analysis["matches"] = [dict(r) for r in cursor.fetchall()]

        return analysis
    finally:
        conn.close()

def get_user_history(user_id: Optional[int] = None, limit: int = 20) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        if user_id:
            cursor.execute(
                """SELECT a.id, a.created_at, a.detector_type, a.model_type, a.status, a.total_time_ms,
                          p.pair_name, p.ref_sensor, p.tgt_sensor, p.target_region,
                          m.verified_inliers_count, m.inlier_ratio_percent, m.rmse_residual_px
                   FROM analyses a
                   JOIN image_pairs p ON a.pair_id = p.id
                   LEFT JOIN metrics m ON a.id = m.analysis_id
                   WHERE a.user_id = ?
                   ORDER BY a.id DESC LIMIT ?""",
                (user_id, limit)
            )
        else:
            cursor.execute(
                """SELECT a.id, a.created_at, a.detector_type, a.model_type, a.status, a.total_time_ms,
                          p.pair_name, p.ref_sensor, p.tgt_sensor, p.target_region,
                          m.verified_inliers_count, m.inlier_ratio_percent, m.rmse_residual_px
                   FROM analyses a
                   JOIN image_pairs p ON a.pair_id = p.id
                   LEFT JOIN metrics m ON a.id = m.analysis_id
                   ORDER BY a.id DESC LIMIT ?""",
                (limit,)
            )
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()
