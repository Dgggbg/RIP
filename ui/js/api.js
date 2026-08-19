/* ================================================================
   api.js — API Service Layer for Clinical RAG
   ----------------------------------------------------------------
   Communicates with the FastAPI endpoints. Isolated from the UI.
   ================================================================ */

'use strict';

const ApiService = {
  /**
   * Sends a medical/clinical question to the RAG backend.
   * @param {string} question - The clinical query from the user.
   * @returns {Promise<object>} The structured RAG response containing recommendation, confidence, evidence, citations.
   */
  async sendQuery(question) {
    try {
      const response = await fetch('/api/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Server returned an error');
      }

      return await response.json();
    } catch (error) {
      console.error('API Query Error:', error);
      throw error;
    }
  },

  /**
   * Checks the health/status of the RAG backend.
   * @returns {Promise<object>} Status metadata.
   */
  async checkHealth() {
    try {
      const response = await fetch('/api/health');
      if (!response.ok) throw new Error('Health check failed');
      return await response.json();
    } catch (error) {
      console.error('API Health Check Error:', error);
      throw error;
    }
  }
};

window.ApiService = ApiService;
