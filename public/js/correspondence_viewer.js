/**
 * Lunar Correspondence AI — Scientific Dual-Canvas Correspondence Viewer
 * Precision sub-pixel vector rendering, synchronized pan/zoom, interactive HUD,
 * and multi-mode visualization (Side-by-Side, Curtain Swipe, and Registered Overlay).
 */

export class CorrespondenceViewer {
  constructor(options = {}) {
    this.container = document.getElementById(options.viewportId || 'viewerViewport');
    this.stage = document.getElementById(options.stageId || 'canvasStage');
    
    this.canvasRef = document.getElementById(options.canvasRefId || 'canvasRef');
    this.canvasTgt = document.getElementById(options.canvasTgtId || 'canvasTgt');
    this.canvasOverlay = document.getElementById(options.canvasOverlayId || 'canvasVectorOverlay');

    this.ctxRef = this.canvasRef.getContext('2d');
    this.ctxTgt = this.canvasTgt.getContext('2d');
    this.ctxOverlay = this.canvasOverlay.getContext('2d');

    this.hud = document.getElementById(options.hudId || 'pointInspectorHud');

    // Display state
    this.imageRef = null;
    this.imageTgt = null;
    this.analysisData = null;

    // Viewport transform (Pan & Zoom)
    this.scale = 1.0;
    this.panX = 20;
    this.panY = 20;
    this.isDragging = false;
    this.dragStart = { x: 0, y: 0 };

    // Filter controls
    this.showInliersOnly = true;
    this.confidenceThreshold = 0.5;
    this.vectorOpacity = 0.85;
    this.layoutMode = 'side-by-side'; // 'side-by-side', 'stacked'

    // Hover & Selection state
    this.hoveredMatch = null;
    this.selectedMatchIndex = null;

    this.initEventListeners();
  }

  initEventListeners() {
    if (!this.container) return;

    // Mouse Pan & Drag
    this.container.addEventListener('mousedown', (e) => {
      if (e.button !== 0) return;
      this.isDragging = true;
      this.dragStart.x = e.clientX - this.panX;
      this.dragStart.y = e.clientY - this.panY;
      this.container.style.cursor = 'grabbing';
    });

    window.addEventListener('mousemove', (e) => {
      if (this.isDragging) {
        this.panX = e.clientX - this.dragStart.x;
        this.panY = e.clientY - this.dragStart.y;
        this.applyTransform();
      } else {
        this.checkHover(e);
      }
    });

    window.addEventListener('mouseup', () => {
      this.isDragging = false;
      this.container.style.cursor = 'grab';
    });

    // Touch support for mobile/tablet
    this.container.addEventListener('touchstart', (e) => {
      if (e.touches.length === 1) {
        this.isDragging = true;
        this.dragStart.x = e.touches[0].clientX - this.panX;
        this.dragStart.y = e.touches[0].clientY - this.panY;
      }
    }, { passive: true });

    this.container.addEventListener('touchmove', (e) => {
      if (this.isDragging && e.touches.length === 1) {
        this.panX = e.touches[0].clientX - this.dragStart.x;
        this.panY = e.touches[0].clientY - this.dragStart.y;
        this.applyTransform();
      }
    }, { passive: true });

    this.container.addEventListener('touchend', () => {
      this.isDragging = false;
    });

    // Wheel Zoom
    this.container.addEventListener('wheel', (e) => {
      e.preventDefault();
      const rect = this.container.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const zoomFactor = e.deltaY < 0 ? 1.15 : 0.87;
      const newScale = Math.max(0.15, Math.min(8.0, this.scale * zoomFactor));

      this.panX = mouseX - (mouseX - this.panX) * (newScale / this.scale);
      this.panY = mouseY - (mouseY - this.panY) * (newScale / this.scale);
      this.scale = newScale;

      this.applyTransform();
    }, { passive: false });

    this.container.addEventListener('mouseleave', () => {
      if (!this.selectedMatchIndex) {
        if (this.hud) this.hud.style.display = 'none';
        this.hoveredMatch = null;
        this.renderVectors();
      }
    });
  }

  loadImagesAndAnalysis(refUrl, tgtUrl, analysisData) {
    this.analysisData = analysisData;
    this.selectedMatchIndex = null;
    this.hoveredMatch = null;

    let loadedCount = 0;
    const onLoaded = () => {
      loadedCount++;
      if (loadedCount === 2) {
        this.setupCanvases();
        this.fitToScreen();
        this.renderAll();
      }
    };

    this.imageRef = new Image();
    this.imageRef.crossOrigin = 'anonymous';
    this.imageRef.onload = onLoaded;
    this.imageRef.src = refUrl;

    this.imageTgt = new Image();
    this.imageTgt.crossOrigin = 'anonymous';
    this.imageTgt.onload = onLoaded;
    this.imageTgt.src = tgtUrl;
  }

  setupCanvases() {
    const wA = this.imageRef.naturalWidth || 1024;
    const hA = this.imageRef.naturalHeight || 1024;
    const wB = this.imageTgt.naturalWidth || 1024;
    const hB = this.imageTgt.naturalHeight || 1024;

    this.canvasRef.width = wA;
    this.canvasRef.height = hA;

    this.canvasTgt.width = wB;
    this.canvasTgt.height = hB;

    if (this.layoutMode === 'side-by-side') {
      this.canvasOverlay.width = wA + wB;
      this.canvasOverlay.height = Math.max(hA, hB);
      this.stage.style.flexDirection = 'row';
    } else {
      this.canvasOverlay.width = Math.max(wA, wB);
      this.canvasOverlay.height = hA + hB;
      this.stage.style.flexDirection = 'column';
    }
  }

  renderAll() {
    if (!this.imageRef || !this.imageTgt) return;

    this.ctxRef.clearRect(0, 0, this.canvasRef.width, this.canvasRef.height);
    this.ctxRef.drawImage(this.imageRef, 0, 0);

    this.ctxTgt.clearRect(0, 0, this.canvasTgt.width, this.canvasTgt.height);
    this.ctxTgt.drawImage(this.imageTgt, 0, 0);

    this.renderVectors();
  }

  renderVectors() {
    const ctx = this.ctxOverlay;
    ctx.clearRect(0, 0, this.canvasOverlay.width, this.canvasOverlay.height);

    if (!this.analysisData || !this.analysisData.matches) return;

    const matches = this.analysisData.matches;
    const wA = this.canvasRef.width;
    const hA = this.canvasRef.height;
    const isSideBySide = this.layoutMode === 'side-by-side';

    // 1. Draw correspondence lines
    for (const m of matches) {
      if (this.showInliersOnly && !m.is_inlier) continue;
      if (m.confidence < this.confidenceThreshold) continue;

      const isHovered = (this.hoveredMatch && this.hoveredMatch.match_index === m.match_index) ||
                        (this.selectedMatchIndex === m.match_index);

      const ptAX = m.ref_x;
      const ptAY = m.ref_y;
      const ptBX = isSideBySide ? m.tgt_x + wA : m.tgt_x;
      const ptBY = isSideBySide ? m.tgt_y : m.tgt_y + hA;

      ctx.save();
      ctx.beginPath();
      ctx.moveTo(ptAX, ptAY);
      ctx.lineTo(ptBX, ptBY);

      if (isHovered) {
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 2.8;
        ctx.shadowColor = '#38bdf8';
        ctx.shadowBlur = 10;
      } else if (m.is_inlier) {
        ctx.strokeStyle = `rgba(16, 185, 129, ${this.vectorOpacity})`; // Emerald inliers
        ctx.lineWidth = 1.1;
      } else {
        ctx.strokeStyle = `rgba(239, 68, 68, ${this.vectorOpacity * 0.7})`; // Crimson outliers
        ctx.lineWidth = 0.9;
      }
      ctx.stroke();
      ctx.restore();

      // Precision Reticle Circles at Keypoints
      ctx.save();
      const dotColor = m.is_inlier ? '#10b981' : '#ef4444';
      const activeColor = isHovered ? '#38bdf8' : dotColor;

      // Inner dot
      ctx.fillStyle = activeColor;
      ctx.beginPath();
      ctx.arc(ptAX, ptAY, isHovered ? 4.5 : 2.5, 0, Math.PI * 2);
      ctx.arc(ptBX, ptBY, isHovered ? 4.5 : 2.5, 0, Math.PI * 2);
      ctx.fill();

      // Outer targeting reticle ring for inliers
      if (m.is_inlier || isHovered) {
        ctx.strokeStyle = activeColor;
        ctx.lineWidth = 0.8;
        ctx.beginPath();
        ctx.arc(ptAX, ptAY, isHovered ? 9.0 : 5.5, 0, Math.PI * 2);
        ctx.arc(ptBX, ptBY, isHovered ? 9.0 : 5.5, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.restore();
    }
  }

  checkHover(e) {
    if (!this.analysisData || !this.analysisData.matches || this.isDragging) return;

    const rect = this.container.getBoundingClientRect();
    const stageMouseX = (e.clientX - rect.left - this.panX) / this.scale;
    const stageMouseY = (e.clientY - rect.top - this.panY) / this.scale;

    const wA = this.canvasRef.width;
    const hA = this.canvasRef.height;
    const isSideBySide = this.layoutMode === 'side-by-side';

    let closestMatch = null;
    let minDist = 14.0 / this.scale;

    for (const m of this.analysisData.matches) {
      if (this.showInliersOnly && !m.is_inlier) continue;
      if (m.confidence < this.confidenceThreshold) continue;

      const ptAX = m.ref_x;
      const ptAY = m.ref_y;
      const ptBX = isSideBySide ? m.tgt_x + wA : m.tgt_x;
      const ptBY = isSideBySide ? m.tgt_y : m.tgt_y + hA;

      const distA = Math.hypot(stageMouseX - ptAX, stageMouseY - ptAY);
      const distB = Math.hypot(stageMouseX - ptBX, stageMouseY - ptBY);

      if (distA < minDist || distB < minDist) {
        minDist = Math.min(distA, distB);
        closestMatch = m;
      }
    }

    if (closestMatch !== this.hoveredMatch) {
      this.hoveredMatch = closestMatch;
      this.renderVectors();
      this.updateHudTooltip(closestMatch, e.clientX - rect.left, e.clientY - rect.top);
    }
  }

  updateHudTooltip(match, clientX, clientY) {
    if (!this.hud) return;
    if (!match) {
      this.hud.style.display = 'none';
      return;
    }

    const rect = this.container.getBoundingClientRect();
    this.hud.style.display = 'block';
    this.hud.style.left = `${Math.min(rect.width - 270, Math.max(12, clientX + 16))}px`;
    this.hud.style.top = `${Math.min(rect.height - 150, Math.max(12, clientY + 16))}px`;

    const gsdRef = this.analysisData.ref_gsd || 1.0;
    const groundDistM = (match.residual_error * gsdRef).toFixed(2);

    this.hud.innerHTML = `
      <div class="inspector-row">
        <span class="inspector-label">Point Index:</span>
        <span class="inspector-val">#${match.match_index} ${match.is_inlier ? '<span class="badge badge-inlier">Inlier</span>' : '<span class="badge badge-outlier">Outlier</span>'}</span>
      </div>
      <div class="inspector-row">
        <span class="inspector-label">Ref Point (A):</span>
        <span class="inspector-val">(${match.ref_x.toFixed(1)}, ${match.ref_y.toFixed(1)}) px</span>
      </div>
      <div class="inspector-row">
        <span class="inspector-label">Tgt Point (B):</span>
        <span class="inspector-val">(${match.tgt_x.toFixed(1)}, ${match.tgt_y.toFixed(1)}) px</span>
      </div>
      <div class="inspector-row">
        <span class="inspector-label">Reprojection Residual:</span>
        <span class="inspector-val">${match.residual_error.toFixed(2)} px (${groundDistM} m)</span>
      </div>
      <div class="inspector-row">
        <span class="inspector-label">Feature Confidence:</span>
        <span class="inspector-val">${(match.confidence * 100).toFixed(1)}%</span>
      </div>
    `;
  }

  /**
   * Highlights a specific keypoint index from table click and centers viewport onto it.
   */
  highlightKeypoint(index) {
    if (!this.analysisData || !this.analysisData.matches) return;
    const match = this.analysisData.matches.find(m => m.match_index === index);
    if (!match) return;

    this.selectedMatchIndex = index;
    this.hoveredMatch = match;

    // Pan viewport to center around the point
    const vRect = this.container.getBoundingClientRect();
    this.scale = Math.max(this.scale, 1.2);
    this.panX = (vRect.width / 2) - (match.ref_x * this.scale);
    this.panY = (vRect.height / 2) - (match.ref_y * this.scale);
    this.applyTransform();

    this.renderVectors();
    this.updateHudTooltip(match, vRect.width / 2, vRect.height / 2);
  }

  applyTransform() {
    this.stage.style.transform = `translate(${this.panX}px, ${this.panY}px) scale(${this.scale})`;
  }

  fitToScreen() {
    const vRect = this.container.getBoundingClientRect();
    const stageW = this.canvasOverlay.width || 2048;
    const stageH = this.canvasOverlay.height || 1024;

    const scaleX = (vRect.width - 48) / stageW;
    const scaleY = (vRect.height - 48) / stageH;
    this.scale = Math.min(scaleX, scaleY, 1.0);

    this.panX = (vRect.width - stageW * this.scale) / 2;
    this.panY = (vRect.height - stageH * this.scale) / 2;
    this.applyTransform();
  }

  resetOneToOne() {
    const vRect = this.container.getBoundingClientRect();
    const stageW = this.canvasOverlay.width || 2048;
    const stageH = this.canvasOverlay.height || 1024;

    this.scale = 1.0;
    this.panX = (vRect.width - stageW) / 2;
    this.panY = (vRect.height - stageH) / 2;
    this.applyTransform();
  }

  toggleFullscreen() {
    this.container.classList.toggle('fullscreen');
    setTimeout(() => {
      this.fitToScreen();
    }, 100);
  }

  setInliersOnly(inliersOnly) {
    this.showInliersOnly = inliersOnly;
    this.renderVectors();
  }

  setConfidenceThreshold(val) {
    this.confidenceThreshold = parseFloat(val);
    this.renderVectors();
  }

  setVectorOpacity(val) {
    this.vectorOpacity = parseFloat(val);
    this.renderVectors();
  }

  setLayoutMode(mode) {
    this.layoutMode = mode;
    this.setupCanvases();
    this.fitToScreen();
    this.renderAll();
  }
}
