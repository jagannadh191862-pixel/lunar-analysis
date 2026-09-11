/**
 * Lunar Correspondence AI — Export & Scientific Report Controller
 * Handles CSV, JSON, and High-Resolution Composite Map generation.
 */

export class ExportController {
  constructor(analysisController) {
    this.analysisController = analysisController;
  }

  getCurrentAnalysisId() {
    return this.analysisController?.currentAnalysis?.id;
  }

  downloadCsv() {
    const id = this.getCurrentAnalysisId();
    if (!id) {
      window.app?.showToast('No active analysis to export.', 'error');
      return;
    }
    window.location.href = `/api/export/${id}/csv`;
  }

  downloadJson() {
    const id = this.getCurrentAnalysisId();
    if (!id) {
      window.app?.showToast('No active analysis to export.', 'error');
      return;
    }
    window.location.href = `/api/export/${id}/json`;
  }

  downloadComposite() {
    const id = this.getCurrentAnalysisId();
    if (!id) {
      window.app?.showToast('No active analysis to export.', 'error');
      return;
    }
    window.location.href = `/api/export/${id}/composite`;
  }

  printScientificReport() {
    const id = this.getCurrentAnalysisId();
    if (!id) {
      window.app?.showToast('No active analysis to print.', 'error');
      return;
    }
    window.print();
  }
}
