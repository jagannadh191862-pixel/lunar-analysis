/**
 * Lunar Correspondence AI — API Client Layer
 * Dedicated scientific service layer for all backend communications.
 */

const API_BASE = '/api';

export const ApiService = {
  /**
   * Fetches curated benchmark datasets with scientific metadata.
   */
  async getDemoPairs() {
    const res = await fetch(`${API_BASE}/demo/pairs`);
    if (!res.ok) throw new Error('Failed to retrieve benchmark datasets.');
    return await res.json();
  },

  /**
   * Fetches details of a specific benchmark pair.
   */
  async loadBenchmarkPair(pairId) {
    const res = await fetch(`${API_BASE}/demo/load/${pairId}`);
    if (!res.ok) throw new Error(`Benchmark dataset ${pairId} could not be loaded.`);
    return await res.json();
  },

  /**
   * Uploads two user-supplied lunar images with sensor metadata.
   */
  async uploadImagePair(formData) {
    const res = await fetch(`${API_BASE}/analysis/upload`, {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) {
      const err = new Error(data.message || data.error || 'Image upload could not be completed.');
      err.data = data;
      throw err;
    }
    return data;
  },

  /**
   * Dispatches planetary correspondence analysis pipeline.
   */
  async runAnalysis(params) {
    const res = await fetch(`${API_BASE}/analysis/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
    const data = await res.json();
    if (!res.ok) {
      const err = new Error(data.message || data.error || 'Analysis could not be completed.');
      err.data = data;
      throw err;
    }
    return data;
  },

  /**
   * Retrieves full analysis record, metrics, and keypoint matches by ID.
   */
  async getAnalysis(analysisId) {
    const res = await fetch(`${API_BASE}/analysis/${analysisId}`);
    if (!res.ok) throw new Error(`Analysis record ${analysisId} not found.`);
    return await res.json();
  },

  /**
   * Retrieves past analysis history.
   */
  async getHistory(limit = 20) {
    const res = await fetch(`${API_BASE}/analysis/history?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to retrieve analysis history.');
    return await res.json();
  },

  /**
   * User authentication methods
   */
  async getCurrentUser() {
    const res = await fetch(`${API_BASE}/auth/me`);
    if (!res.ok) return { authenticated: false };
    return await res.json();
  },

  async login(username, password) {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Authentication failed.');
    return data;
  },

  async register(username, email, password, institution) {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password, institution }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Registration failed.');
    return data;
  },

  async logout() {
    const res = await fetch(`${API_BASE}/auth/logout`, { method: 'POST' });
    return await res.json();
  }
};
