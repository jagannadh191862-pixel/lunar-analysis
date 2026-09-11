/**
 * Lunar Correspondence AI — Mission History & Archive Controller
 * Browsing past planetary analyses, telemetry comparison, and one-click inspection.
 */

import { ApiService } from './api.js';

export class HistoryController {
  constructor(analysisController, options = {}) {
    this.analysisController = analysisController;
    this.historyTableBody = document.getElementById(options.tableBodyId || 'historyTableBody');
    this.historyCount = document.getElementById(options.countId || 'historyCount');
  }

  async loadHistory() {
    if (!this.historyTableBody) return;
    try {
      this.historyTableBody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:24px; color:var(--text-muted);">Loading telemetry archive...</td></tr>';
      const data = await ApiService.getHistory(25);
      const history = data.history || [];

      if (this.historyCount) {
        this.historyCount.textContent = `${history.length} Records`;
      }

      if (history.length === 0) {
        this.historyTableBody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:32px; color:var(--text-muted);">No archived analyses found. Run a benchmark or upload imagery to begin.</td></tr>';
        return;
      }

      let html = '';
      for (const item of history) {
        const inlierCount = item.verified_inliers_count ?? '—';
        const inlierRatio = item.inlier_ratio_percent != null ? `${item.inlier_ratio_percent.toFixed(1)}%` : '—';
        const rmse = item.rmse_residual_px != null ? `${item.rmse_residual_px.toFixed(3)} px` : '—';
        const dateStr = item.created_at ? item.created_at.split(' ')[0] : '—';

        html += `
          <tr style="border-bottom:1px solid var(--border-subtle); transition:background var(--transition-fast);">
            <td style="padding:12px; font-family:var(--font-mono); font-size:0.8125rem; color:var(--text-muted);">#${item.id}</td>
            <td style="padding:12px; font-weight:500; color:var(--text-primary);">${item.pair_name}</td>
            <td style="padding:12px; font-size:0.8125rem; color:var(--text-secondary);">${item.ref_sensor} ↔ ${item.tgt_sensor}</td>
            <td style="padding:12px; font-family:var(--font-mono); font-size:0.8125rem; color:var(--status-inlier);">${inlierCount} (${inlierRatio})</td>
            <td style="padding:12px; font-family:var(--font-mono); font-size:0.8125rem; color:#e2e8f0;">${rmse}</td>
            <td style="padding:12px; font-family:var(--font-mono); font-size:0.75rem; color:var(--text-muted);">${dateStr}</td>
            <td style="padding:12px; text-align:right;">
              <button class="btn btn-secondary btn-sm" onclick="window.historyController.inspectPastAnalysis(${item.id})">Inspect</button>
            </td>
          </tr>
        `;
      }
      this.historyTableBody.innerHTML = html;
    } catch (e) {
      this.historyTableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:24px; color:var(--status-outlier);">Failed to load history: ${e.message}</td></tr>`;
    }
  }

  async inspectPastAnalysis(analysisId) {
    try {
      window.app?.switchTab('tabAnalyze');
      const data = await ApiService.getAnalysis(analysisId);
      this.analysisController.currentAnalysis = data.analysis;
      this.analysisController.renderResults(data.analysis);
      window.app?.showToast(`Loaded analysis #${analysisId}`, 'success');
    } catch (err) {
      window.app?.showErrorModal('Failed to load analysis', err.message);
    }
  }
}
