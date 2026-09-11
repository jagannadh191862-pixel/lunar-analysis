"""
Lunar Correspondence Vision Engine — Vercel-Compatible (scikit-image)
Scientific Multi-Modal Feature Extraction, Descriptor Matching,
and RANSAC Geometric Verification for Planetary Remote Sensing Imagery.
Uses scikit-image + scipy instead of opencv to stay within Vercel's 50MB bundle limit.
"""

import time
import json
import logging
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger("lunar_vision_engine")
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# Try opencv first (local dev), fall back to scikit-image (Vercel)
# ---------------------------------------------------------------------------
try:
    import cv2 as _cv2
    _BACKEND = "opencv"
except ImportError:
    _cv2 = None
    _BACKEND = "skimage"

try:
    from PIL import Image
    import io
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

try:
    from skimage import io as sk_io
    from skimage.color import rgb2gray
    from skimage.exposure import equalize_adapthist
    from skimage.feature import ORB, SIFT, match_descriptors
    from skimage.measure import ransac
    from skimage.transform import ProjectiveTransform, AffineTransform, resize
    _SKIMAGE_OK = True
except ImportError:
    _SKIMAGE_OK = False

logger.info(f"Vision Engine Backend: {_BACKEND} | skimage={_SKIMAGE_OK} | PIL={_PIL_OK}")


class LunarVisionEngine:
    """
    High-precision computer vision pipeline for lunar surface correspondence.
    Handles high-contrast shadowed terrain, scale disparities (TMC-2 vs OHRC),
    and illumination variation across planetary orbital passes.
    """

    def __init__(self):
        pass

    # ------------------------------------------------------------------
    # Image Loading
    # ------------------------------------------------------------------
    def _load_gray(self, image_path: str) -> np.ndarray:
        """Load image and return normalised uint8 grayscale array."""
        p = Path(image_path)
        if not p.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        if _BACKEND == "opencv":
            img = _cv2.imread(str(p), _cv2.IMREAD_UNCHANGED)
            if img is None:
                raise ValueError(f"cv2 could not decode: {image_path}")
            if len(img.shape) == 3:
                gray = _cv2.cvtColor(img, _cv2.COLOR_BGR2GRAY)
            else:
                gray = img
            if gray.dtype != np.uint8:
                gray = _cv2.normalize(gray, None, 0, 255, _cv2.NORM_MINMAX, dtype=_cv2.CV_8U)
            return gray

        # scikit-image / PIL fallback
        if _PIL_OK:
            with Image.open(str(p)) as im:
                im_arr = np.array(im.convert("L"))  # L = 8-bit grayscale
            return im_arr.astype(np.uint8)

        if _SKIMAGE_OK:
            raw = sk_io.imread(str(p))
            if raw.ndim == 3:
                gray = rgb2gray(raw)
            else:
                gray = raw.astype(float) / max(raw.max(), 1)
            gray_u8 = (gray * 255).astype(np.uint8)
            return gray_u8

        raise RuntimeError("No image-loading library available (cv2 / PIL / skimage).")

    def _clahe(self, gray: np.ndarray) -> np.ndarray:
        """Contrast-limited adaptive histogram equalisation."""
        if _BACKEND == "opencv":
            clahe = _cv2.createCLAHE(clipLimit=2.8, tileGridSize=(8, 8))
            return clahe.apply(gray)
        # scikit-image version: equalize_adapthist expects float [0,1]
        norm = gray.astype(np.float32) / 255.0
        eq = equalize_adapthist(norm, clip_limit=0.011)
        return (eq * 255).astype(np.uint8)

    # ------------------------------------------------------------------
    # Feature Extraction
    # ------------------------------------------------------------------
    def _extract_orb_opencv(self, gray: np.ndarray, n_features: int = 1000):
        orb = _cv2.ORB_create(nfeatures=n_features, scaleFactor=1.2, nlevels=8)
        kps, descs = orb.detectAndCompute(gray, None)
        if descs is None:
            return np.empty((0, 2), dtype=np.float32), np.empty((0, 32), dtype=np.uint8)
        pts = np.array([[kp.pt[0], kp.pt[1]] for kp in kps], dtype=np.float32)
        return pts, descs

    def _extract_sift_opencv(self, gray: np.ndarray, n_features: int = 500):
        sift = _cv2.SIFT_create(nfeatures=n_features)
        kps, descs = sift.detectAndCompute(gray, None)
        if descs is None:
            return np.empty((0, 2), dtype=np.float32), np.empty((0, 128), dtype=np.float32)
        pts = np.array([[kp.pt[0], kp.pt[1]] for kp in kps], dtype=np.float32)
        return pts, descs

    def _extract_akaze_opencv(self, gray: np.ndarray):
        akaze = _cv2.AKAZE_create()
        kps, descs = akaze.detectAndCompute(gray, None)
        if descs is None:
            return np.empty((0, 2), dtype=np.float32), np.empty((0, 61), dtype=np.uint8)
        pts = np.array([[kp.pt[0], kp.pt[1]] for kp in kps], dtype=np.float32)
        return pts, descs

    def _extract_orb_skimage(self, gray: np.ndarray, n_keypoints: int = 500):
        detector = ORB(n_keypoints=n_keypoints, fast_n=9, fast_threshold=0.08)
        detector.detect_and_extract(gray.astype(np.float32) / 255.0)
        return detector.keypoints[:, ::-1].astype(np.float32), detector.descriptors

    def _extract_sift_skimage(self, gray: np.ndarray):
        try:
            detector = SIFT()
            detector.detect_and_extract(gray.astype(np.float32) / 255.0)
            return detector.keypoints[:, ::-1].astype(np.float32), detector.descriptors
        except Exception:
            return self._extract_orb_skimage(gray)

    def _extract_features(self, gray: np.ndarray, detector_type: str):
        if _BACKEND == "opencv":
            if detector_type == "SIFT":
                return self._extract_sift_opencv(gray)
            elif detector_type == "AKAZE":
                return self._extract_akaze_opencv(gray)
            else:
                return self._extract_orb_opencv(gray)
        else:
            if detector_type == "SIFT":
                return self._extract_sift_skimage(gray)
            else:
                return self._extract_orb_skimage(gray)

    # ------------------------------------------------------------------
    # Descriptor Matching
    # ------------------------------------------------------------------
    def _match_opencv(self, descs_ref, descs_tgt, detector_type: str, ratio_threshold: float):
        if detector_type in ("SIFT",):
            bf = _cv2.BFMatcher(_cv2.NORM_L2, crossCheck=False)
        else:
            bf = _cv2.BFMatcher(_cv2.NORM_HAMMING, crossCheck=False)
        raw = bf.knnMatch(descs_ref, descs_tgt, k=2)
        good = [(m.queryIdx, m.trainIdx, m.distance)
                for m, n in raw if len([m, n]) == 2 and m.distance < ratio_threshold * n.distance]
        return good

    def _match_skimage(self, descs_ref, descs_tgt, ratio_threshold: float):
        """Binary descriptor matching via Hamming distance with ratio test."""
        if descs_ref.dtype == bool:
            matches = match_descriptors(descs_ref, descs_tgt, metric="hamming",
                                        cross_check=True, max_ratio=ratio_threshold)
        else:
            matches = match_descriptors(descs_ref, descs_tgt, metric="euclidean",
                                        cross_check=True, max_ratio=ratio_threshold)
        # returns Nx2 array of [ref_idx, tgt_idx]
        return [(int(m[0]), int(m[1]), 0.0) for m in matches]

    # ------------------------------------------------------------------
    # RANSAC Geometric Verification
    # ------------------------------------------------------------------
    def _ransac_opencv(self, pts_ref, pts_tgt, matches, model_type: str, ransac_threshold: float):
        if len(matches) < 4:
            return [], None, []
        src = np.float32([pts_ref[m[0]] for m in matches]).reshape(-1, 1, 2)
        dst = np.float32([pts_tgt[m[1]] for m in matches]).reshape(-1, 1, 2)
        if model_type == "AFFINE":
            H, mask = _cv2.estimateAffine2D(src, dst, method=_cv2.RANSAC,
                                             ransacReprojThreshold=ransac_threshold)
        else:
            H, mask = _cv2.findHomography(src, dst, _cv2.RANSAC, ransac_threshold)
        if H is None or mask is None:
            return [], None, []
        inlier_idx = [i for i, v in enumerate(mask.ravel()) if v]
        return inlier_idx, H, mask.ravel().tolist()

    def _ransac_skimage(self, pts_ref, pts_tgt, matches, model_type: str, ransac_threshold: float):
        if len(matches) < 4:
            return [], None, []
        src = np.array([[pts_ref[m[0]][0], pts_ref[m[0]][1]] for m in matches], dtype=np.float64)
        dst = np.array([[pts_tgt[m[1]][0], pts_tgt[m[1]][1]] for m in matches], dtype=np.float64)
        Model = AffineTransform if model_type == "AFFINE" else ProjectiveTransform
        try:
            model_robust, inlier_mask = ransac(
                (src, dst), Model,
                min_samples=4,
                residual_threshold=ransac_threshold,
                max_trials=500
            )
            inlier_idx = [i for i, v in enumerate(inlier_mask) if v]
            H = model_robust.params if model_robust else None
            return inlier_idx, H, inlier_mask.tolist()
        except Exception as e:
            logger.warning(f"RANSAC failed: {e}")
            return [], None, []

    # ------------------------------------------------------------------
    # Main Pipeline
    # ------------------------------------------------------------------
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

        t_total = time.perf_counter()

        # Stage 1: Preprocessing
        t0 = time.perf_counter()
        gray_ref = self._load_gray(ref_image_path)
        gray_tgt = self._load_gray(tgt_image_path)
        h_ref, w_ref = gray_ref.shape[:2]
        h_tgt, w_tgt = gray_tgt.shape[:2]

        if clahe_enabled:
            gray_ref = self._clahe(gray_ref)
            gray_tgt = self._clahe(gray_tgt)
        preprocessing_ms = (time.perf_counter() - t0) * 1000

        # Stage 2: Feature Extraction
        t0 = time.perf_counter()
        pts_ref, descs_ref = self._extract_features(gray_ref, detector_type)
        pts_tgt, descs_tgt = self._extract_features(gray_tgt, detector_type)
        extraction_ms = (time.perf_counter() - t0) * 1000

        kp_ref_count = len(pts_ref)
        kp_tgt_count = len(pts_tgt)

        if kp_ref_count < 4 or kp_tgt_count < 4 or descs_ref is None or descs_tgt is None:
            raise ValueError(
                f"Insufficient keypoints for correspondence: ref={kp_ref_count}, tgt={kp_tgt_count}. "
                "Try a higher-resolution image or a different detector."
            )

        # Stage 3: Descriptor Matching with Lowe ratio test
        t0 = time.perf_counter()
        if _BACKEND == "opencv":
            matches = self._match_opencv(descs_ref, descs_tgt, detector_type, ratio_threshold)
        else:
            matches = self._match_skimage(descs_ref, descs_tgt, ratio_threshold)
        matching_ms = (time.perf_counter() - t0) * 1000
        initial_match_count = len(matches)

        # Stage 4: RANSAC Geometric Verification
        t0 = time.perf_counter()
        if _BACKEND == "opencv":
            inlier_idx, H, mask = self._ransac_opencv(pts_ref, pts_tgt, matches, model_type, ransac_threshold)
        else:
            inlier_idx, H, mask = self._ransac_skimage(pts_ref, pts_tgt, matches, model_type, ransac_threshold)
        verification_ms = (time.perf_counter() - t0) * 1000

        inlier_count = len(inlier_idx)
        inlier_ratio = (inlier_count / initial_match_count * 100) if initial_match_count > 0 else 0.0
        inlier_set = set(inlier_idx)

        # Stage 5: Geometric Decomposition
        estimated_scale = 1.0
        estimated_rotation_deg = 0.0
        estimated_tx = 0.0
        estimated_ty = 0.0
        rmse = 0.0
        H_json = "null"

        if H is not None:
            H_arr = np.array(H)
            H_json = json.dumps(H_arr.tolist())
            if model_type == "AFFINE" and H_arr.shape == (2, 3):
                estimated_scale = float(np.sqrt(abs(np.linalg.det(H_arr[:, :2]))))
                estimated_rotation_deg = float(np.degrees(np.arctan2(H_arr[1, 0], H_arr[0, 0])))
                estimated_tx = float(H_arr[0, 2])
                estimated_ty = float(H_arr[1, 2])
            elif H_arr.shape == (3, 3):
                estimated_scale = float(np.sqrt(abs(np.linalg.det(H_arr[:2, :2]))))
                estimated_rotation_deg = float(np.degrees(np.arctan2(H_arr[1, 0], H_arr[0, 0])))
                estimated_tx = float(H_arr[0, 2])
                estimated_ty = float(H_arr[1, 2])

            # RMSE on inliers
            if inlier_idx:
                residuals = []
                H_arr_f = H_arr.astype(np.float64)
                for i in inlier_idx:
                    m = matches[i]
                    rx, ry = float(pts_ref[m[0]][0]), float(pts_ref[m[0]][1])
                    tx, ty = float(pts_tgt[m[1]][0]), float(pts_tgt[m[1]][1])
                    src_h = np.array([rx, ry, 1.0])
                    if model_type == "AFFINE" and H_arr_f.shape == (2, 3):
                        proj = H_arr_f @ src_h
                        residuals.append(np.sqrt((proj[0]-tx)**2 + (proj[1]-ty)**2))
                    else:
                        proj = H_arr_f @ src_h
                        if abs(proj[2]) > 1e-9:
                            proj = proj / proj[2]
                        residuals.append(np.sqrt((proj[0]-tx)**2 + (proj[1]-ty)**2))
                rmse = float(np.sqrt(np.mean(np.array(residuals)**2))) if residuals else 0.0

        total_ms = (time.perf_counter() - t_total) * 1000

        # Build match records
        match_records = []
        for i, m in enumerate(matches):
            r_idx, t_idx = m[0], m[1]
            rx, ry = float(pts_ref[r_idx][0]), float(pts_ref[r_idx][1])
            tx, ty = float(pts_tgt[t_idx][0]), float(pts_tgt[t_idx][1])
            dist = float(m[2])
            confidence = max(0.0, min(1.0, 1.0 - dist / 512.0)) if dist > 0 else 0.85
            is_inlier = i in inlier_set
            residual = 0.0
            if is_inlier and H is not None:
                H_arr_f = np.array(H).astype(np.float64)
                src_h = np.array([rx, ry, 1.0])
                if model_type == "AFFINE" and H_arr_f.shape == (2, 3):
                    proj = H_arr_f @ src_h
                    residual = float(np.sqrt((proj[0]-tx)**2 + (proj[1]-ty)**2))
                else:
                    proj = H_arr_f @ src_h
                    if abs(proj[2]) > 1e-9:
                        proj = proj / proj[2]
                    residual = float(np.sqrt((proj[0]-tx)**2 + (proj[1]-ty)**2))

            match_records.append({
                "ref_x": rx, "ref_y": ry,
                "tgt_x": tx, "tgt_y": ty,
                "confidence": round(confidence, 4),
                "is_inlier": is_inlier,
                "residual_error": round(residual, 4)
            })

        metrics = {
            "keypoints_ref_count": kp_ref_count,
            "keypoints_tgt_count": kp_tgt_count,
            "initial_matches_count": initial_match_count,
            "verified_inliers_count": inlier_count,
            "inlier_ratio_percent": round(inlier_ratio, 2),
            "rmse_residual_px": round(rmse, 4),
            "estimated_scale": round(estimated_scale, 6),
            "estimated_rotation_deg": round(estimated_rotation_deg, 4),
            "estimated_translation_x": round(estimated_tx, 4),
            "estimated_translation_y": round(estimated_ty, 4),
            "transform_matrix_json": H_json,
            "preprocessing_ms": round(preprocessing_ms, 2),
            "extraction_ms": round(extraction_ms, 2),
            "matching_ms": round(matching_ms, 2),
            "verification_ms": round(verification_ms, 2),
            "total_time_ms": round(total_ms, 2),
            "ref_dimensions": f"{w_ref}x{h_ref}",
            "tgt_dimensions": f"{w_tgt}x{h_tgt}",
            "backend": _BACKEND,
            "detector": detector_type,
            "model": model_type,
        }

        return {"metrics": metrics, "matches": match_records}


vision_engine = LunarVisionEngine()
