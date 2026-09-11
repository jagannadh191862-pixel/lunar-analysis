-- Lunar Correspondence AI Database Schema
-- Strict relational integrity for planetary science analysis and correspondence records

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    role TEXT DEFAULT 'researcher',
    institution TEXT DEFAULT 'Planetary Remote Sensing Laboratory',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS image_pairs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NULL,
    pair_name TEXT NOT NULL,
    is_demo INTEGER DEFAULT 0,
    target_region TEXT DEFAULT 'Lunar Surface',
    center_latitude REAL DEFAULT 0.0,
    center_longitude REAL DEFAULT 0.0,
    ref_image_path TEXT NOT NULL,
    ref_sensor TEXT NOT NULL,
    ref_gsd REAL DEFAULT 1.0,
    ref_sun_elevation REAL DEFAULT 15.0,
    tgt_image_path TEXT NOT NULL,
    tgt_sensor TEXT NOT NULL,
    tgt_gsd REAL DEFAULT 1.0,
    tgt_sun_elevation REAL DEFAULT 15.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pair_id INTEGER NOT NULL,
    user_id INTEGER NULL,
    detector_type TEXT NOT NULL DEFAULT 'ORB',
    model_type TEXT NOT NULL DEFAULT 'HOMOGRAPHY',
    ransac_threshold REAL DEFAULT 2.5,
    ratio_threshold REAL DEFAULT 0.75,
    clahe_enabled INTEGER DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'COMPLETED',
    error_message TEXT NULL,
    total_time_ms REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pair_id) REFERENCES image_pairs(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER UNIQUE NOT NULL,
    keypoints_ref_count INTEGER NOT NULL,
    keypoints_tgt_count INTEGER NOT NULL,
    initial_matches_count INTEGER NOT NULL,
    verified_inliers_count INTEGER NOT NULL,
    inlier_ratio_percent REAL NOT NULL,
    rmse_residual_px REAL NOT NULL,
    estimated_scale REAL NOT NULL,
    estimated_rotation_deg REAL NOT NULL,
    estimated_translation_x REAL NOT NULL,
    estimated_translation_y REAL NOT NULL,
    transform_matrix_json TEXT NOT NULL,
    preprocessing_ms REAL DEFAULT 0.0,
    extraction_ms REAL DEFAULT 0.0,
    matching_ms REAL DEFAULT 0.0,
    verification_ms REAL DEFAULT 0.0,
    FOREIGN KEY (analysis_id) REFERENCES analyses(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS keypoint_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL,
    match_index INTEGER NOT NULL,
    ref_x REAL NOT NULL,
    ref_y REAL NOT NULL,
    tgt_x REAL NOT NULL,
    tgt_y REAL NOT NULL,
    confidence REAL NOT NULL,
    is_inlier INTEGER NOT NULL DEFAULT 1,
    residual_error REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY (analysis_id) REFERENCES analyses(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_analyses_pair_id ON analyses(pair_id);
CREATE INDEX IF NOT EXISTS idx_analyses_user_id ON analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_keypoint_matches_analysis ON keypoint_matches(analysis_id);
CREATE INDEX IF NOT EXISTS idx_keypoint_matches_inlier ON keypoint_matches(analysis_id, is_inlier);
