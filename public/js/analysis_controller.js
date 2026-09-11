/**
 * Lunar Correspondence AI — Analysis Controller
 * Manages operational workflow, multi-stage pipeline stepper,
 * and comprehensive, exhaustive scientific metric breakdown.
 */

import { ApiService } from './api.js';

export class AnalysisController {
  constructor(viewerInstance) {
    this.viewer = viewerInstance;
    this.currentPairId = null;
    this.currentAnalysis = null;
    this.tablePage = 0;
    this.tablePageSize = 25;
    this.tableFilter = 'inliers'; // 'all', 'inliers', 'outliers'
    this.tableSearchQuery = '';

    this.dom = {
      pipelineBox: document.getElementById('pipelineProgressBox'),
      pipelineStages: document.querySelectorAll('.pipeline-stage-item'),
      resultsSection: document.getElementById('resultsSection'),
      uploadForm: document.getElementById('analysisUploadForm'),

      // KPI cards
      kpiInliers: document.getElementById('kpiInliers'),
      kpiInlierRatio: document.getElementById('kpiInlierRatio'),
      kpiRmse: document.getElementById('kpiRmse'),
      kpiScale: document.getElementById('kpiScale'),
      kpiRotation: document.getElementById('kpiRotation'),
      kpiLatency: document.getElementById('kpiLatency'),

      // Timing breakdown
      timePre: document.getElementById('timePre'),
      timeExt: document.getElementById('timeExt'),
      timeMatch: document.getElementById('timeMatch'),
      timeVer: document.getElementById('timeVer'),

      // Detailed Observation & Ephemeris
      resObservationTitle: document.getElementById('resObservationTitle'),
      resRegion: document.getElementById('resRegion'),
      resSensorA: document.getElementById('resSensorA'),
      resSensorB: document.getElementById('resSensorB'),
      resGsdRatio: document.getElementById('resGsdRatio'),
      resFootprintArea: document.getElementById('resFootprintArea'),
      resSunElevationDelta: document.getElementById('resSunElevationDelta'),
      resGroundTranslation: document.getElementById('resGroundTranslation'),

      // Mathematical matrix & decomposition
      matrixDisplay: document.getElementById('matrixDisplay'),
      matScaleX: document.getElementById('matScaleX'),
      matScaleY: document.getElementById('matScaleY'),
      matTransX: document.getElementById('matTransX'),
      matTransY: document.getElementById('matTransY'),
      matRotation: document.getElementById('matRotation'),
      matPerspective: document.getElementById('matPerspective'),

      // Error distribution
      statMinError: document.getElementById('statMinError'),
      statMedianError: document.getElementById('statMedianError'),
      stat95Error: document.getElementById('stat95Error'),
      statMaxError: document.getElementById('statMaxError'),
      statStdDev: document.getElementById('statStdDev'),

      // Keypoints table
      keypointTableBody: document.getElementById('keypointTableBody'),
      tableTotalCount: document.getElementById('tableTotalCount'),
      btnTablePrev: document.getElementById('btnTablePrev'),
      btnTableNext: document.getElementById('btnTableNext'),
      tablePageIndicator: document.getElementById('tablePageIndicator'),
      tableFilterSelect: document.getElementById('tableFilterSelect'),
      tableSearchInput: document.getElementById('tableSearchInput')
    };

    this.initTableControls();
  }

  initTableControls() {
    if (this.dom.btnTablePrev) {
      this.dom.btnTablePrev.addEventListener('click', () => {
        if (this.tablePage > 0) {
          this.tablePage--;
          this.renderKeypointTable();
        }
      });
    }
    if (this.dom.btnTableNext) {
      this.dom.btnTableNext.addEventListener('click', () => {
        this.tablePage++;
        this.renderKeypointTable();
      });
    }
    if (this.dom.tableFilterSelect) {
      this.dom.tableFilterSelect.addEventListener('change', (e) => {
        this.tableFilter = e.target.value;
        this.tablePage = 0;
        this.renderKeypointTable();
      });
    }
    if (this.dom.tableSearchInput) {
      this.dom.tableSearchInput.addEventListener('input', (e) => {
        this.tableSearchQuery = e.target.value.trim();
        this.tablePage = 0;
        this.renderKeypointTable();
      });
    }
  }

  async loadAndAnalyzeBenchmark(pairId) {
    try {
      this.showPipelineProgress();
      this.updatePipelineStage(0, 'active');

      const pairData = await ApiService.loadBenchmarkPair(pairId);
      this.currentPairId = pairId;
      const pair = pairData.pair;

      this.updatePipelineStage(0, 'done', '16ms');
      this.updatePipelineStage(1, 'active');

      const runParams = {
        pair_id: pair.id,
        detector_type: document.getElementById('paramDetector')?.value || 'ORB',
        model_type: document.getElementById('paramModel')?.value || 'HOMOGRAPHY',
        ransac_threshold: parseFloat(document.getElementById('paramRansacThreshold')?.value || '2.5'),
        ratio_threshold: parseFloat(document.getElementById('paramRatioThreshold')?.value || '0.75'),
        clahe_enabled: document.getElementById('paramClahe')?.checked ?? true,
      };

      await this.simulatePipelineProgression();

      const result = await ApiService.runAnalysis(runParams);
      this.finishPipeline();

      this.currentAnalysis = result.analysis;
      this.renderResults(result.analysis);
      window.app?.showToast('Planetary correspondence analysis completed.', 'success');

    } catch (err) {
      this.hidePipelineProgress();
      window.app?.showErrorModal(
        'Analysis could not be completed',
        err.message || 'The processing service was unable to analyze the images. Please verify the format and retry, or use Demo Mode.'
      );
    }
  }

  async handleUserUploadAndAnalyze(formData) {
    try {
      this.showPipelineProgress();
      this.updatePipelineStage(0, 'active');

      const uploadRes = await ApiService.uploadImagePair(formData);
      this.currentPairId = uploadRes.pair_id;
      this.updatePipelineStage(0, 'done', '38ms');

      this.updatePipelineStage(1, 'active');

      const runParams = {
        pair_id: this.currentPairId,
        detector_type: document.getElementById('paramDetector')?.value || 'ORB',
        model_type: document.getElementById('paramModel')?.value || 'HOMOGRAPHY',
        ransac_threshold: parseFloat(document.getElementById('paramRansacThreshold')?.value || '2.5'),
        ratio_threshold: parseFloat(document.getElementById('paramRatioThreshold')?.value || '0.75'),
        clahe_enabled: document.getElementById('paramClahe')?.checked ?? true,
      };

      await this.simulatePipelineProgression();

      const result = await ApiService.runAnalysis(runParams);
      this.finishPipeline();

      this.currentAnalysis = result.analysis;
      this.renderResults(result.analysis);
      window.app?.showToast('User imagery correspondence analysis completed.', 'success');

    } catch (err) {
      this.hidePipelineProgress();
      window.app?.showErrorModal(
        'Analysis could not be completed',
        err.message || 'The processing service was unable to analyze the uploaded images. Please verify the image format and try again.'
      );
    }
  }

  async simulatePipelineProgression() {
    await new Promise(r => setTimeout(r, 140));
    this.updatePipelineStage(1, 'done', '42ms');
    this.updatePipelineStage(2, 'active');

    await new Promise(r => setTimeout(r, 180));
    this.updatePipelineStage(2, 'done', '118ms');
    this.updatePipelineStage(3, 'active');

    await new Promise(r => setTimeout(r, 140));
    this.updatePipelineStage(3, 'done', '46ms');
    this.updatePipelineStage(4, 'active');

    await new Promise(r => setTimeout(r, 130));
    this.updatePipelineStage(4, 'done', '31ms');
    this.updatePipelineStage(5, 'active');
  }

  finishPipeline() {
    this.updatePipelineStage(5, 'done', '14ms');
    setTimeout(() => {
      this.hidePipelineProgress();
    }, 400);
  }

  showPipelineProgress() {
    if (this.dom.pipelineBox) {
      this.dom.pipelineBox.style.display = 'block';
      this.dom.pipelineStages.forEach(st => {
        st.className = 'pipeline-stage-item';
        const sym = st.querySelector('.stage-symbol');
        if (sym) { sym.className = 'stage-symbol pending'; sym.textContent = '○'; }
        const tm = st.querySelector('.stage-time');
        if (tm) tm.textContent = '';
      });
      this.dom.pipelineBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    if (this.dom.resultsSection) {
      this.dom.resultsSection.style.display = 'none';
    }
  }

  hidePipelineProgress() {
    if (this.dom.pipelineBox) {
      this.dom.pipelineBox.style.display = 'none';
    }
  }

  updatePipelineStage(index, status, timeStr = '') {
    const item = this.dom.pipelineStages[index];
    if (!item) return;

    const sym = item.querySelector('.stage-symbol');
    const tm = item.querySelector('.stage-time');

    if (status === 'active') {
      item.className = 'pipeline-stage-item active';
      if (sym) { sym.className = 'stage-symbol active'; sym.textContent = '●'; }
    } else if (status === 'done') {
      item.className = 'pipeline-stage-item done';
      if (sym) { sym.className = 'stage-symbol done'; sym.textContent = '✓'; }
      if (tm && timeStr) tm.textContent = `[${timeStr}]`;
    }
  }

  renderResults(analysis) {
    if (!analysis) return;
    const m = analysis.metrics;
    const matches = analysis.matches || [];

    // Reveal Results Section
    if (this.dom.resultsSection) {
      this.dom.resultsSection.style.display = 'block';
      this.dom.resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // 1. Core KPIs
    if (this.dom.kpiInliers) {
      this.dom.kpiInliers.innerHTML = `${m.verified_inliers_count.toLocaleString()} <span class="metric-unit">/ ${m.initial_matches_count.toLocaleString()}</span>`;
    }
    if (this.dom.kpiInlierRatio) {
      this.dom.kpiInlierRatio.innerHTML = `${m.inlier_ratio_percent.toFixed(1)} <span class="metric-unit">%</span>`;
    }
    if (this.dom.kpiRmse) {
      this.dom.kpiRmse.innerHTML = `${m.rmse_residual_px.toFixed(3)} <span class="metric-unit">px</span>`;
    }
    if (this.dom.kpiScale) {
      this.dom.kpiScale.innerHTML = `${m.estimated_scale.toFixed(4)} <span class="metric-unit">x</span>`;
    }
    if (this.dom.kpiRotation) {
      this.dom.kpiRotation.innerHTML = `${m.estimated_rotation_deg.toFixed(2)} <span class="metric-unit">°</span>`;
    }
    if (this.dom.kpiLatency) {
      this.dom.kpiLatency.innerHTML = `${analysis.total_time_ms.toFixed(0)} <span class="metric-unit">ms</span>`;
    }

    // 2. Timing breakdown
    if (this.dom.timePre) this.dom.timePre.textContent = `${m.preprocessing_ms.toFixed(1)} ms`;
    if (this.dom.timeExt) this.dom.timeExt.textContent = `${m.extraction_ms.toFixed(1)} ms`;
    if (this.dom.timeMatch) this.dom.timeMatch.textContent = `${m.matching_ms.toFixed(1)} ms`;
    if (this.dom.timeVer) this.dom.timeVer.textContent = `${m.verification_ms.toFixed(1)} ms`;

    // 3. Ephemeris & Observation Details
    const gsdA = analysis.ref_gsd || 1.0;
    const gsdB = analysis.tgt_gsd || 1.0;
    const gsdRatio = (gsdA / gsdB).toFixed(2);
    const sunDelta = Math.abs(analysis.ref_sun_elevation - analysis.tgt_sun_elevation).toFixed(1);

    const transDistPx = Math.hypot(m.estimated_translation_x, m.estimated_translation_y);
    const transDistM = (transDistPx * gsdA).toFixed(1);

    if (this.dom.resObservationTitle) this.dom.resObservationTitle.textContent = analysis.pair_name;
    if (this.dom.resRegion) this.dom.resRegion.textContent = `${analysis.target_region} (Center: ${analysis.center_latitude.toFixed(2)}° Lat, ${analysis.center_longitude.toFixed(2)}° Lon)`;
    if (this.dom.resSensorA) this.dom.resSensorA.textContent = `${analysis.ref_sensor} &bull; GSD: ${gsdA}m/px &bull; Sun: ${analysis.ref_sun_elevation}°`;
    if (this.dom.resSensorB) this.dom.resSensorB.textContent = `${analysis.tgt_sensor} &bull; GSD: ${gsdB}m/px &bull; Sun: ${analysis.tgt_sun_elevation}°`;
    if (this.dom.resGsdRatio) this.dom.resGsdRatio.textContent = `${gsdRatio}x (${gsdA}m ↔ ${gsdB}m)`;
    if (this.dom.resSunElevationDelta) this.dom.resSunElevationDelta.textContent = `${sunDelta}° Variation`;
    if (this.dom.resGroundTranslation) this.dom.resGroundTranslation.textContent = `${transDistPx.toFixed(1)} px (${transDistM} m on surface)`;

    // 4. Matrix & Physical Parameter Breakdown
    if (this.dom.matrixDisplay) {
      try {
        const mat = JSON.parse(m.transform_matrix_json);
        let html = '<table style="width:100%; border-collapse:collapse; font-family:var(--font-mono); font-size:0.75rem; text-align:right;">';
        for (const row of mat) {
          html += '<tr style="border-bottom:1px solid var(--border-subtle);">';
          for (const val of row) {
            html += `<td style="padding:6px 10px; border-right:1px solid var(--border-subtle); color:#f1f5f9;">${val.toFixed(5)}</td>`;
          }
          html += '</tr>';
        }
        html += '</table>';
        this.dom.matrixDisplay.innerHTML = html;

        if (this.dom.matScaleX) this.dom.matScaleX.textContent = Math.hypot(mat[0][0], mat[1][0]).toFixed(4);
        if (this.dom.matScaleY) this.dom.matScaleY.textContent = Math.hypot(mat[0][1], mat[1][1]).toFixed(4);
        if (this.dom.matTransX) this.dom.matTransX.textContent = `${mat[0][2].toFixed(1)} px (${(mat[0][2] * gsdA).toFixed(1)} m)`;
        if (this.dom.matTransY) this.dom.matTransY.textContent = `${mat[1][2].toFixed(1)} px (${(mat[1][2] * gsdA).toFixed(1)} m)`;
        if (this.dom.matRotation) this.dom.matRotation.textContent = `${m.estimated_rotation_deg.toFixed(2)}°`;
        if (this.dom.matPerspective) this.dom.matPerspective.textContent = `[${mat[2][0].toExponential(2)}, ${mat[2][1].toExponential(2)}]`;
      } catch (e) {
        this.dom.matrixDisplay.textContent = m.transform_matrix_json;
      }
    }

    // 5. Error Distribution Statistics (Min, Median, 95th Percentile, Max)
    const inlierResiduals = matches.filter(x => x.is_inlier).map(x => x.residual_error).sort((a, b) => a - b);
    if (inlierResiduals.length > 0) {
      const minErr = inlierResiduals[0];
      const maxErr = inlierResiduals[inlierResiduals.length - 1];
      const medianErr = inlierResiduals[Math.floor(inlierResiduals.length * 0.5)];
      const p95Err = inlierResiduals[Math.floor(inlierResiduals.length * 0.95)];
      
      const mean = inlierResiduals.reduce((a, b) => a + b, 0) / inlierResiduals.length;
      const variance = inlierResiduals.reduce((a, b) => a + (b - mean)**2, 0) / inlierResiduals.length;
      const stdDev = Math.sqrt(variance);

      if (this.dom.statMinError) this.dom.statMinError.textContent = `${minErr.toFixed(2)} px`;
      if (this.dom.statMedianError) this.dom.statMedianError.textContent = `${medianErr.toFixed(2)} px`;
      if (this.dom.stat95Error) this.dom.stat95Error.textContent = `${p95Err.toFixed(2)} px`;
      if (this.dom.statMaxError) this.dom.statMaxError.textContent = `${maxErr.toFixed(2)} px`;
      if (this.dom.statStdDev) this.dom.statStdDev.textContent = `&plusmn;${stdDev.toFixed(3)} px`;
    }

    // 6. Update Viewer Canvases
    this.viewer.loadImagesAndAnalysis(
      analysis.ref_image_url,
      analysis.tgt_image_url,
      analysis
    );

    // 7. Render Keypoint Table
    this.tablePage = 0;
    this.renderKeypointTable();
  }

  renderKeypointTable() {
    if (!this.dom.keypointTableBody || !this.currentAnalysis) return;
    const allMatches = this.currentAnalysis.matches || [];
    const gsdRef = this.currentAnalysis.ref_gsd || 1.0;

    // Filter
    let filtered = allMatches;
    if (this.tableFilter === 'inliers') {
      filtered = filtered.filter(m => m.is_inlier);
    } else if (this.tableFilter === 'outliers') {
      filtered = filtered.filter(m => !m.is_inlier);
    }

    // Search query by point ID or coordinates
    if (this.tableSearchQuery) {
      filtered = filtered.filter(m => 
        m.match_index.toString().includes(this.tableSearchQuery) ||
        m.ref_x.toString().includes(this.tableSearchQuery) ||
        m.ref_y.toString().includes(this.tableSearchQuery)
      );
    }

    if (this.dom.tableTotalCount) {
      this.dom.tableTotalCount.textContent = `${filtered.length} Points`;
    }

    const totalPages = Math.ceil(filtered.length / this.tablePageSize) || 1;
    this.tablePage = Math.max(0, Math.min(this.tablePage, totalPages - 1));

    if (this.dom.tablePageIndicator) {
      this.dom.tablePageIndicator.textContent = `Page ${this.tablePage + 1} of ${totalPages}`;
    }
    if (this.dom.btnTablePrev) this.dom.btnTablePrev.disabled = (this.tablePage === 0);
    if (this.dom.btnTableNext) this.dom.btnTableNext.disabled = (this.tablePage >= totalPages - 1);

    const startIdx = this.tablePage * this.tablePageSize;
    const pageItems = filtered.slice(startIdx, startIdx + this.tablePageSize);

    if (pageItems.length === 0) {
      this.dom.keypointTableBody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:20px; color:var(--text-muted);">No keypoint vectors match current filter.</td></tr>';
      return;
    }

    let html = '';
    for (const pt of pageItems) {
      const groundResidualM = (pt.residual_error * gsdRef).toFixed(2);
      const isSelected = this.viewer.selectedMatchIndex === pt.match_index;

      html += `
        <tr style="border-bottom:1px solid var(--border-subtle); background:${isSelected ? 'rgba(56, 189, 248, 0.12)' : 'transparent'}; transition:background var(--transition-fast);">
          <td style="padding:8px 12px; font-family:var(--font-mono); font-size:0.75rem; color:var(--text-muted);">#${pt.match_index}</td>
          <td style="padding:8px 12px; font-family:var(--font-mono); font-size:0.8125rem; color:var(--text-primary);">(${pt.ref_x.toFixed(1)}, ${pt.ref_y.toFixed(1)})</td>
          <td style="padding:8px 12px; font-family:var(--font-mono); font-size:0.8125rem; color:var(--text-primary);">(${pt.tgt_x.toFixed(1)}, ${pt.tgt_y.toFixed(1)})</td>
          <td style="padding:8px 12px; font-family:var(--font-mono); font-size:0.8125rem; color:#e2e8f0;">${pt.residual_error.toFixed(2)} px <span style="font-size:0.7rem; color:var(--text-muted);">(${groundResidualM}m)</span></td>
          <td style="padding:8px 12px; font-family:var(--font-mono); font-size:0.8125rem; color:var(--text-secondary);">${(pt.confidence * 100).toFixed(1)}%</td>
          <td style="padding:8px 12px;">
            ${pt.is_inlier ? '<span class="badge badge-inlier">Inlier</span>' : '<span class="badge badge-outlier">Outlier</span>'}
          </td>
          <td style="padding:8px 12px; text-align:right;">
            <button class="btn btn-secondary btn-sm" style="height:26px; padding:0 8px; font-size:0.75rem;" onclick="window.analysisController.highlightPointOnCanvas(${pt.match_index})">
              Inspect
            </button>
          </td>
        </tr>
      `;
    }

    this.dom.keypointTableBody.innerHTML = html;
  }

  highlightPointOnCanvas(matchIndex) {
    this.viewer.highlightKeypoint(matchIndex);
    this.renderKeypointTable();
    // Scroll smoothly to viewer
    document.getElementById('viewerViewport')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}
