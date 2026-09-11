# LUNAR CORRESPONDENCE AI
**Aerospace-Grade Multi-Modal Feature Extraction & RANSAC Geometric Verification Platform**

---

## 1. Executive Summary

**Lunar Correspondence AI** is an aerospace-grade planetary science and remote-sensing software system. It solves the critical problem of multi-sensor, multi-illumination, and multi-temporal image correspondence across lunar surface imagery.

Modeled after the **ISRO Chandrayaan-2** mission instruments:
- **TMC-2 (Terrain Mapping Camera-2)**: Regional survey panchromatic stereo (5.0 m/pixel GSD).
- **OHRC (Orbiter High Resolution Camera)**: Ultra-high-resolution hazard and micro-crater characterization (0.32 m/pixel GSD).

Alongside international lunar datasets (**LROC NAC/WAC**), the platform provides automated radiometric shadow equalization, multi-scale descriptor extraction, and RANSAC projective homography estimation to recover sub-pixel correspondence vectors.

---

## 2. Key Architecture & Capabilities

### Scientific Computer Vision Engine
- **Radiometric Normalization**: Contrast-Limited Adaptive Histogram Equalization (CLAHE) with bilateral filtering to enhance subtle micro-crater topography embedded in deep permanent shadow regions (PSR).
- **Multi-Scale Descriptors**: Support for ORB (Oriented FAST and Rotated BRIEF), SIFT (Scale-Invariant Feature Transform), and AKAZE (Non-linear scale-space).
- **Cross-Matching with Lowe's Ratio Test**: Eliminates ambiguous repetitive regolith textures via mutual nearest neighbor matching ($d_1 / d_2 < \tau$).
- **RANSAC Geometric Verification**: Evaluates 8-DOF Projective Homography ($3 \times 3$) and Affine ($2 \times 3$) models to separate true geometric inliers from spurious visual noise.
- **Physical Parameter Recovery**: Calculates inlier ratio (%), residual RMSE (pixels), relative scale factor ($s$), and rotation angle ($\theta^\circ$).

### Aerospace User Experience & Visualization
- **3D Chandrayaan-2 Orbital Scene**: Physically grounded lunar sphere with terminator day/night line shading, procedural maria and crater highlands, Chandrayaan-2 orbiter model (solar array wings + parabolic antenna), and real-time orbital telemetry HUD.
- **Dual-Canvas Interactive Viewer**: Synchronized pan and zoom, sub-pixel vector line rendering, verified inlier/outlier color coding (emerald green vs muted crimson), dynamic confidence threshold slider, and floating precision hover HUD.
- **Authentic Pipeline Stepper**: Multi-stage progress tracking (`Image validation` → `Preprocessing` → `Feature extraction` → `Multi-modal matching` → `Geometric verification` → `Result generation`).
- **Data Product Exports**: One-click download of matched keypoints (CSV), formal laboratory reports (JSON), high-resolution composite maps (PNG), and printable audit sheets.

---

## 3. Directory Layout

```
lunar-correspondence-ai/
├── backend/
│   ├── app.py                     # Master Flask application server
│   ├── config.py                  # Storage paths, limits, and server config
│   ├── api/
│   │   ├── routes_auth.py         # User authentication & session handling
│   │   ├── routes_analysis.py     # Image upload, validation & analysis execution
│   │   ├── routes_demo.py         # Verified benchmark dataset loader
│   │   └── routes_export.py       # CSV, JSON, and PNG composite map exports
│   ├── engine/
│   │   └── vision_engine.py       # Multi-scale detection, CLAHE, and RANSAC verification
│   ├── db/
│   │   ├── schema.sql             # Relational SQLite database schema
│   │   └── database.py            # SQLite connection pool & query methods
│   ├── data/
│   │   ├── benchmark_pairs/       # Pre-calibrated Chandrayaan-2 & LROC images
│   │   └── metadata.json          # Scientific ground-truth metadata
│   └── storage/
│       └── uploads/               # Persistent storage for uploaded imagery
├── frontend/
│   ├── index.html                 # Main single-page application interface
│   ├── css/
│   │   ├── variables.css          # Aerospace design system tokens
│   │   ├── base.css               # Reset, typography, navigation, and layout
│   │   ├── components.css         # Buttons, cards, dropzones, pipeline stepper
│   │   ├── orbit.css              # 3D Moon canvas and orbital telemetry HUD
│   │   ├── viewer.css             # Dual-canvas correspondence viewer styling
│   │   └── responsive.css         # Breakpoint rules (375px to 1920px)
│   └── js/
│       ├── app.js                 # Global router, tab switching, and event manager
│       ├── api.js                 # REST API client layer
│       ├── orbit_scene.js         # Realistic Moon and Chandrayaan-2 orbit canvas
│       ├── correspondence_viewer.js # Synchronized zoom/pan, vector overlay, and HUD
│       ├── analysis_controller.js # Multi-stage stepper & metrics rendering
│       ├── history_controller.js  # Telemetry archive and past analysis inspection
│       └── export_controller.js   # Data export triggers
├── run.sh                         # Unified launch script
└── README.md
```

---

## 4. Launching the System

```bash
cd /Users/Jagan-MacBookPro/.gemini/antigravity-ide/scratch/lunar-correspondence-ai
./run.sh
```

Navigate to **http://localhost:5050** in any modern web browser.
