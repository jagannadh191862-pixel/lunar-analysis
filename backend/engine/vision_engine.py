"""
Lunar Correspondence Vision Engine
Scientific Multi-Modal Feature Extraction, Descriptor Matching,
and RANSAC Geometric Verification for Planetary Remote Sensing Imagery.
"""

import time
import json
import logging
import numpy as np
import cv2
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger("lunar_vision_engine")
logging.basicConfig(level=logging.INFO)

class LunarVisionEngine:
    """
    High-precision computer vision pipeline designed for lunar surface correspondence.
    Handles high-contrast shadowed terrain, scale disparities (e.g. TMC-2 vs OHRC),
    and illumination variation across planetary orbital passes.
    """

    def __init__(self):
        pass

    def load_and_preprocess(self, image_path: str, clahe_enabled: bool = True) -> Tuple[np.ndarray, np.ndarray, float]:
        """
        Loads an image from disk, converts to 8-bit single-channel lunar grayscale,
        and applies Contrast-Limited Adaptive Histogram Equalization (CLAHE) for shadowed crater recovery.
        Returns: (raw_gray, processed_gray, elapsed_ms)
        """
        t0 = time.perf_counter()
        p = Path(image_path)
        if not p.exists():
            raise FileNotFoundError(f"Image not found at path: {image_path}")

        img = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
        if img is None:
            raise ValueError(f"Failed to decode image data: {image_path}")

        # Convert to single-channel 8-bit grayscale
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        if gray.dtype != np.uint8:
            gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)

        raw_gray = gray.copy()

        # CLAHE enhances micro-topography in permanent shadow regions (PSR)
        if clahe_enabled:
            clahe = cv2.createCLAHE(clipLimit=2.8, tileGridSize=(8, 8))
            processed_gray = clahe.apply(raw_gray)
        else:
            processed_gray = raw_gray

        # Subtle bilateral filtering to suppress sensor read noise while preserving sharp crater rim edges
        processed_gray = cv2.bilateralFilter(processed_gray, d=5, sigmaColor=25, sigmaSpace=25)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return raw_gray, processed_gray, elapsed_ms

    def extract_features(self, gray_img: np.ndarray, detector_type: str = "ORB") -> Tuple[List[cv2.KeyPoint], np.ndarray, float]:
        """
        Extracts multi-scale planetary keypoints and compact descriptors.
        Supported detectors: 'ORB', 'SIFT', 'AKAZE'
        """
        t0 = time.perf_counter()
        detector_type = detector_type.upper()

        if detector_type == "SIFT":
            # Scale-Invariant Feature Transform: optimal for extreme resolution disparity (TMC-2 vs OHRC)
            detector = cv2.SIFT_create(
                nfeatures=2500,
                nOctaveLayers=4,
                contrastThreshold=0.03,
                edgeThreshold=12,
                sigma=1.6
            )
        elif detector_type == "AKAZE":
            detector = cv2.AKAZE_create(
                descriptor_type=cv2.AKAZE_DESCRIPTOR_MLDB,
                descriptor_size=0,
                descriptor_channels=3,
                threshold=0.001
            )
        else: # Default ORB
            # Oriented FAST and Rotated BRIEF: robust and fast for real-time analysis
            detector = cv2.ORB_create(
                nfeatures=3000,
                scaleFactor=1.2,
                nlevels=8,
                edgeThreshold=15,
                firstLevel=0,
                WTA_K=2,
                scoreType=cv2.ORB_HARRIS_SCORE,
                patchSize=31,
                fastThreshold=12
            )

        keypoints, descriptors = detector.detectAndCompute(gray_img, None)

        if descriptors is None:
            keypoints = []
            descriptors = np.empty((0, 32 if detector_type == "ORB" else 128), dtype=np.uint8)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return keypoints, descriptors, elapsed_ms

    def match_features(
        self,
        desc_a: np.ndarray,
        desc_b: np.ndarray,
        detector_type: str = "ORB",
        ratio_threshold: float = 0.75
    ) -> Tuple[List[cv2.DMatch], float]:
        """
        Performs descriptor matching with Lowe's Ratio Test to reject ambiguous texture matches.
        """
        t0 = time.perf_counter()
        detector_type = detector_type.upper()

        if desc_a is None or desc_b is None or len(desc_a) == 0 or len(desc_b) == 0:
            return [], (time.perf_counter() - t0) * 1000.0

        # Select norm based on descriptor binary/float type
        if detector_type in ["ORB", "AKAZE"]:
            matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        else:
            matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)

        # k-NN match with k=2 for ratio test
        try:
            raw_matches = matcher.knnMatch(desc_a, desc_b, k=2)
        except Exception as e:
            logger.warning(f"Matcher error: {e}")
            return [], (time.perf_counter() - t0) * 1000.0

        good_matches = []
        for match_pair in raw_matches:
            if len(match_pair) == 2:
                m, n = match_pair
                if m.distance < ratio_threshold * n.distance:
                    good_matches.append(m)
            elif len(match_pair) == 1:
                good_matches.append(match_pair[0])

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return good_matches, elapsed_ms

    def geometric_verification(
        self,
        kp_a: List[cv2.KeyPoint],
        kp_b: List[cv2.KeyPoint],
        matches: List[cv2.DMatch],
        model_type: str = "HOMOGRAPHY",
        ransac_threshold: float = 2.5
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float]:
        """
        Estimates the rigid or projective planetary transformation matrix using RANSAC.
        Calculates per-point reprojection residuals and inlier mask.
        Returns: (matrix, inlier_mask, residuals, elapsed_ms)
        """
        t0 = time.perf_counter()
        model_type = model_type.upper()

        if len(matches) < 4:
            return np.eye(3), np.zeros(len(matches), dtype=bool), np.zeros(len(matches)), (time.perf_counter() - t0) * 1000.0

        pts_a = np.float32([kp_a[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        pts_b = np.float32([kp_b[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)

        inlier_mask = np.zeros(len(matches), dtype=bool)
        residuals = np.zeros(len(matches), dtype=np.float64)

        if model_type == "AFFINE":
            # Affine model (scale, rotation, translation, shear)
            matrix_2x3, inliers = cv2.estimateAffine2D(
                pts_a, pts_b,
                method=cv2.RANSAC,
                ransacReprojThreshold=ransac_threshold,
                maxIters=3000,
                confidence=0.99
            )
            if matrix_2x3 is not None:
                matrix = np.eye(3, dtype=np.float64)
                matrix[0:2, :] = matrix_2x3
                inlier_mask = (inliers.ravel() == 1)

                # Calculate reprojection residuals
                ones = np.ones((len(pts_a), 1, 1), dtype=np.float32)
                pts_a_homo = np.concatenate([pts_a, ones], axis=2).reshape(-1, 3)
                projected = (matrix @ pts_a_homo.T).T[:, 0:2]
                residuals = np.linalg.norm(projected - pts_b.reshape(-1, 2), axis=1)
            else:
                matrix = np.eye(3)
        else: # Default HOMOGRAPHY
            # Projective Homography: accounts for sensor perspective shift across oblique lunar angles
            matrix, inliers = cv2.findHomography(
                pts_a, pts_b,
                method=cv2.RANSAC,
                ransacReprojThreshold=ransac_threshold,
                maxIters=4000,
                confidence=0.995
            )
            if matrix is not None and inliers is not None:
                inlier_mask = (inliers.ravel() == 1)
                # Compute projective reprojection residuals
                projected = cv2.perspectiveTransform(pts_a, matrix)
                residuals = np.linalg.norm(projected.reshape(-1, 2) - pts_b.reshape(-1, 2), axis=1)
            else:
                matrix = np.eye(3)

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return matrix, inlier_mask, residuals, elapsed_ms

    def analyze_pair(
        self,
        ref_image_path: str,
        tgt_image_path: str,
        detector_type: str = "ORB",
        model_type: str = "HOMOGRAPHY",
        ransac_threshold: float = 2.5,
        ratio_threshold: float = 0.75,
        clahe_enabled: bool = True
    ) -> Dict[str, Any]:
        """
        Executes full scientific analysis pipeline on an image pair.
        Returns complete metrics and individual correspondence vector coordinates.
        """
        total_t0 = time.perf_counter()

        # Stage 1: Validation and Preprocessing
        raw_ref, prep_ref, prep_ref_ms = self.load_and_preprocess(ref_image_path, clahe_enabled)
        raw_tgt, prep_tgt, prep_tgt_ms = self.load_and_preprocess(tgt_image_path, clahe_enabled)
        preprocessing_ms = prep_ref_ms + prep_tgt_ms

        # Stage 2: Feature Extraction
        kp_ref, desc_ref, ext_ref_ms = self.extract_features(prep_ref, detector_type)
        kp_tgt, desc_tgt, ext_tgt_ms = self.extract_features(prep_tgt, detector_type)
        extraction_ms = ext_ref_ms + ext_tgt_ms

        # Stage 3: Multi-Modal Matching
        matches, matching_ms = self.match_features(desc_ref, desc_tgt, detector_type, ratio_threshold)

        # Stage 4: Geometric Verification via RANSAC
        matrix, inlier_mask, residuals, verification_ms = self.geometric_verification(
            kp_ref, kp_tgt, matches, model_type, ransac_threshold
        )

        total_time_ms = (time.perf_counter() - total_t0) * 1000.0

        # Calculate scientific metrics
        total_matches = len(matches)
        verified_inliers = int(np.sum(inlier_mask))
        inlier_ratio = (verified_inliers / total_matches * 100.0) if total_matches > 0 else 0.0

        if verified_inliers > 0:
            rmse_px = float(np.sqrt(np.mean(residuals[inlier_mask] ** 2)))
        else:
            rmse_px = 0.0

        # Decompose transformation matrix to physical parameters
        scale_x = float(np.sqrt(matrix[0, 0]**2 + matrix[1, 0]**2))
        scale_y = float(np.sqrt(matrix[0, 1]**2 + matrix[1, 1]**2))
        estimated_scale = float((scale_x + scale_y) / 2.0)
        rotation_rad = float(np.arctan2(matrix[1, 0], matrix[0, 0]))
        rotation_deg = float(np.degrees(rotation_rad))
        translation_x = float(matrix[0, 2])
        translation_y = float(matrix[1, 2])

        # Prepare matched vector coordinates
        matches_data = []
        max_dist = max([m.distance for m in matches]) if matches else 1.0
        if max_dist <= 0:
            max_dist = 1.0

        for i, m in enumerate(matches):
            pt_a = kp_ref[m.queryIdx].pt
            pt_b = kp_tgt[m.trainIdx].pt
            is_in = bool(inlier_mask[i])
            res = float(residuals[i])
            # Normalize confidence: high distance = lower confidence, inliers get confidence boost
            conf = max(0.05, min(0.99, 1.0 - (m.distance / (max_dist * 1.3))))
            if not is_in:
                conf *= 0.6

            matches_data.append({
                "match_index": i,
                "ref_x": round(float(pt_a[0]), 2),
                "ref_y": round(float(pt_a[1]), 2),
                "tgt_x": round(float(pt_b[0]), 2),
                "tgt_y": round(float(pt_b[1]), 2),
                "confidence": round(float(conf), 4),
                "is_inlier": is_in,
                "residual_error": round(res, 2)
            })

        metrics = {
            "keypoints_ref_count": len(kp_ref),
            "keypoints_tgt_count": len(kp_tgt),
            "initial_matches_count": total_matches,
            "verified_inliers_count": verified_inliers,
            "inlier_ratio_percent": round(inlier_ratio, 2),
            "rmse_residual_px": round(rmse_px, 3),
            "estimated_scale": round(estimated_scale, 4),
            "estimated_rotation_deg": round(rotation_deg, 2),
            "estimated_translation_x": round(translation_x, 2),
            "estimated_translation_y": round(translation_y, 2),
            "transform_matrix_json": json.dumps(matrix.tolist()),
            "preprocessing_ms": round(preprocessing_ms, 2),
            "extraction_ms": round(extraction_ms, 2),
            "matching_ms": round(matching_ms, 2),
            "verification_ms": round(verification_ms, 2),
            "total_time_ms": round(total_time_ms, 2),
            "image_ref_width": raw_ref.shape[1],
            "image_ref_height": raw_ref.shape[0],
            "image_tgt_width": raw_tgt.shape[1],
            "image_tgt_height": raw_tgt.shape[0]
        }

        return {
            "metrics": metrics,
            "matches": matches_data
        }

# Global singleton
vision_engine = LunarVisionEngine()
