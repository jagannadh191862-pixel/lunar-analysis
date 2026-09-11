/**
 * Lunar Correspondence AI — Master Application Orchestrator
 * Global state management, tab routing, event delegation, and UI lifecycle.
 */

import { ApiService } from './api.js';
import { OrbitScene } from './orbit_scene.js';
import { CorrespondenceViewer } from './correspondence_viewer.js';
import { AnalysisController } from './analysis_controller.js';
import { HistoryController } from './history_controller.js';
import { ExportController } from './export_controller.js';

class LunarApp {
  constructor() {
    this.currentUser = null;
    this.activeTab = 'tabHero';

    // Initialize sub-controllers
    this.viewer = new CorrespondenceViewer({
      viewportId: 'viewerViewport',
      stageId: 'canvasStage',
      canvasRefId: 'canvasRef',
      canvasTgtId: 'canvasTgt',
      canvasOverlayId: 'canvasVectorOverlay',
      hudId: 'pointInspectorHud'
    });

    this.analysisController = new AnalysisController(this.viewer);
    this.historyController = new HistoryController(this.analysisController);
    this.exportController = new ExportController(this.analysisController);

    // Expose to window for inline onclick handlers if needed
    window.app = this;
    window.analysisController = this.analysisController;
    window.historyController = this.historyController;
    window.exportController = this.exportController;
    window.viewer = this.viewer;
  }

  async init() {
    // 1. Initialize Realistic 3D Moon & Chandrayaan-2 Orbit Scene
    this.orbitScene = new OrbitScene('orbitCanvas', {
      altitude: document.getElementById('hudAltitude'),
      velocity: document.getElementById('hudVelocity'),
      lat: document.getElementById('hudLat'),
      lon: document.getElementById('hudLon'),
      anomaly: document.getElementById('hudAnomaly'),
    });

    // 2. Fetch User Session
    await this.checkUserSession();

    // 3. Load Benchmarks into Quick Strip
    await this.loadBenchmarkCards();

    // 4. Setup Event Listeners
    this.bindEvents();

    // 5. Check URL hash for direct tab navigation
    this.handleHashChange();
    window.addEventListener('hashchange', () => this.handleHashChange());
  }

  async checkUserSession() {
    try {
      const data = await ApiService.getCurrentUser();
      this.currentUser = data.user;
      const userBadge = document.getElementById('userSessionBadge');
      if (userBadge && this.currentUser) {
        userBadge.textContent = this.currentUser.username;
      }
    } catch (e) {
      console.warn('Session check fallback:', e);
    }
  }

  async loadBenchmarkCards() {
    const strip = document.getElementById('benchmarkCardGrid');
    if (!strip) return;
    try {
      const data = await ApiService.getDemoPairs();
      const pairs = data.benchmark_pairs || [];
      let html = '';
      for (const p of pairs) {
        html += `
          <div class="benchmark-card" onclick="window.app.triggerBenchmarkAnalysis(${p.id})">
            <div class="benchmark-card-top">
              <div class="benchmark-title">${p.pair_name}</div>
              <span class="badge badge-sensor">${p.ref_sensor.split(' ')[0]}</span>
            </div>
            <p style="font-size:0.8125rem; color:var(--text-secondary); margin-bottom:8px;">${p.description}</p>
            <div class="benchmark-meta">
              <span>Region: ${p.target_region.split('/')[0]}</span>
              <span>GSD: ${p.ref_gsd}m ↔ ${p.tgt_gsd}m</span>
            </div>
          </div>
        `;
      }
      strip.innerHTML = html;
    } catch (e) {
      console.error('Failed to load benchmarks:', e);
    }
  }

  bindEvents() {
    // Tab Switching
    document.querySelectorAll('[data-tab]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const tab = btn.getAttribute('data-tab');
        this.switchTab(tab);
      });
    });

    // Mobile nav toggle
    const navToggle = document.getElementById('mobileNavToggle');
    const mainNav = document.getElementById('mainNav');
    if (navToggle && mainNav) {
      navToggle.addEventListener('click', () => {
        mainNav.classList.toggle('mobile-open');
      });
    }

    // Hero CTAs
    const btnStartAnalysis = document.getElementById('btnStartAnalysis');
    if (btnStartAnalysis) {
      btnStartAnalysis.addEventListener('click', () => {
        this.switchTab('tabAnalyze');
      });
    }

    const btnTryLiveDemo = document.getElementById('btnTryLiveDemo');
    if (btnTryLiveDemo) {
      btnTryLiveDemo.addEventListener('click', () => {
        this.switchTab('tabAnalyze');
        this.triggerBenchmarkAnalysis(1);
      });
    }

    // Benchmark Selector Dropdown in Analyze tab
    const demoSelect = document.getElementById('selectBenchmarkPair');
    if (demoSelect) {
      demoSelect.addEventListener('change', (e) => {
        const val = e.target.value;
        if (val) {
          this.triggerBenchmarkAnalysis(parseInt(val, 10));
        }
      });
    }

    // User Upload Form Submission
    const uploadForm = document.getElementById('analysisUploadForm');
    if (uploadForm) {
      uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(uploadForm);
        await this.analysisController.handleUserUploadAndAnalyze(formData);
      });
    }

    // File input previews
    this.setupDropzonePreview('refImageInput', 'refDropzonePreview', 'refDropzonePrompt');
    this.setupDropzonePreview('tgtImageInput', 'tgtDropzonePreview', 'tgtDropzonePrompt');

    // Viewer Controls
    const toggleInliers = document.getElementById('viewerToggleInliers');
    if (toggleInliers) {
      toggleInliers.addEventListener('change', (e) => {
        this.viewer.setInliersOnly(e.target.checked);
      });
    }

    const sliderConfidence = document.getElementById('viewerConfidenceSlider');
    const labelConfidence = document.getElementById('viewerConfidenceVal');
    if (sliderConfidence) {
      sliderConfidence.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        if (labelConfidence) labelConfidence.textContent = `${(val * 100).toFixed(0)}%`;
        this.viewer.setConfidenceThreshold(val);
      });
    }

    const sliderOpacity = document.getElementById('viewerOpacitySlider');
    const labelOpacity = document.getElementById('viewerOpacityVal');
    if (sliderOpacity) {
      sliderOpacity.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        if (labelOpacity) labelOpacity.textContent = `${(val * 100).toFixed(0)}%`;
        this.viewer.setVectorOpacity(val);
      });
    }

    const btnFitScreen = document.getElementById('btnViewerFitScreen');
    if (btnFitScreen) btnFitScreen.addEventListener('click', () => this.viewer.fitToScreen());

    const btnOneToOne = document.getElementById('btnViewerOneToOne');
    if (btnOneToOne) btnOneToOne.addEventListener('click', () => this.viewer.resetOneToOne());

    const btnFullscreen = document.getElementById('btnViewerFullscreen');
    if (btnFullscreen) btnFullscreen.addEventListener('click', () => this.viewer.toggleFullscreen());

    const selectLayout = document.getElementById('viewerSelectLayout');
    if (selectLayout) {
      selectLayout.addEventListener('change', (e) => {
        this.viewer.setLayoutMode(e.target.value);
      });
    }

    // Export Action Buttons
    document.getElementById('btnExportCsv')?.addEventListener('click', () => this.exportController.downloadCsv());
    document.getElementById('btnExportJson')?.addEventListener('click', () => this.exportController.downloadJson());
    document.getElementById('btnExportComposite')?.addEventListener('click', () => this.exportController.downloadComposite());
    document.getElementById('btnPrintReport')?.addEventListener('click', () => this.exportController.printScientificReport());

    // Auth Modal Actions
    document.getElementById('btnOpenAuthModal')?.addEventListener('click', () => this.openAuthModal());
    document.getElementById('btnCloseAuthModal')?.addEventListener('click', () => this.closeAuthModal());
    document.getElementById('authForm')?.addEventListener('submit', (e) => this.handleAuthSubmit(e));
  }

  setupDropzonePreview(inputId, previewId, promptId) {
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);
    const prompt = document.getElementById(promptId);

    if (!input || !preview) return;

    input.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (re) => {
          preview.src = re.target.result;
          preview.style.display = 'block';
          if (prompt) prompt.style.display = 'none';
        };
        reader.readAsDataURL(file);
      }
    });
  }

  triggerBenchmarkAnalysis(pairId) {
    this.switchTab('tabAnalyze');
    this.analysisController.loadAndAnalyzeBenchmark(pairId);
  }

  switchTab(tabId) {
    this.activeTab = tabId;

    // Update nav link active styles
    document.querySelectorAll('[data-tab]').forEach(el => {
      if (el.getAttribute('data-tab') === tabId) {
        el.classList.add('active');
      } else {
        el.classList.remove('active');
      }
    });

    // Close mobile nav drawer if open
    document.getElementById('mainNav')?.classList.remove('mobile-open');

    // Toggle tab page sections
    const tabs = ['tabHero', 'tabAnalyze', 'tabHistory', 'tabMethodology'];
    for (const t of tabs) {
      const el = document.getElementById(t);
      if (el) {
        el.style.display = (t === tabId) ? 'block' : 'none';
      }
    }

    // On history tab switch, load history
    if (tabId === 'tabHistory') {
      this.historyController.loadHistory();
    }

    // On analyze tab, trigger resize/fit
    if (tabId === 'tabAnalyze' && this.viewer) {
      setTimeout(() => this.viewer.fitToScreen(), 120);
    }

    window.location.hash = tabId;
  }

  handleHashChange() {
    const hash = window.location.hash.replace('#', '');
    if (['tabHero', 'tabAnalyze', 'tabHistory', 'tabMethodology'].includes(hash)) {
      this.switchTab(hash);
    }
  }

  openAuthModal() {
    const modal = document.getElementById('authModal');
    if (modal) modal.classList.add('active');
  }

  closeAuthModal() {
    const modal = document.getElementById('authModal');
    if (modal) modal.classList.remove('active');
  }

  async handleAuthSubmit(e) {
    e.preventDefault();
    const isRegister = document.getElementById('authRegisterToggle')?.checked;
    const username = document.getElementById('authUsername')?.value;
    const email = document.getElementById('authEmail')?.value;
    const password = document.getElementById('authPassword')?.value;
    const institution = document.getElementById('authInstitution')?.value;

    try {
      if (isRegister) {
        await ApiService.register(username, email, password, institution);
        this.showToast('Scientist account created successfully.', 'success');
      } else {
        await ApiService.login(username, password);
        this.showToast('Authenticated successfully.', 'success');
      }
      this.closeAuthModal();
      await this.checkUserSession();
    } catch (err) {
      this.showToast(err.message, 'error');
    }
  }

  showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type === 'error' ? 'toast-error' : type === 'success' ? 'toast-success' : ''}`;
    toast.innerHTML = `
      <div style="font-family:var(--font-mono); font-size:0.75rem; color:${type === 'error' ? '#f87171' : '#34d399'};">
        ${type === 'error' ? '✖' : '✔'}
      </div>
      <div>${message}</div>
    `;

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 250);
    }, 4200);
  }

  showErrorModal(title, message, canRetry = true) {
    const modal = document.getElementById('errorModal');
    const titleEl = document.getElementById('errorModalTitle');
    const msgEl = document.getElementById('errorModalMessage');
    const btnRetry = document.getElementById('btnErrorRetry');
    const btnDemo = document.getElementById('btnErrorDemo');

    if (!modal) return;
    if (titleEl) titleEl.textContent = title;
    if (msgEl) msgEl.textContent = message;

    if (btnRetry) {
      btnRetry.style.display = canRetry ? 'inline-flex' : 'none';
      btnRetry.onclick = () => {
        modal.classList.remove('active');
        const uploadForm = document.getElementById('analysisUploadForm');
        if (uploadForm) uploadForm.requestSubmit();
      };
    }

    if (btnDemo) {
      btnDemo.onclick = () => {
        modal.classList.remove('active');
        this.triggerBenchmarkAnalysis(1);
      };
    }

    modal.classList.add('active');
  }
}

// Bootstrap on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
  const app = new LunarApp();
  app.init();
});
