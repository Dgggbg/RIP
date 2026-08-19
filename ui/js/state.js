/* ================================================================
   state.js — Conversation and Language State Management
   ----------------------------------------------------------------
   Maintains the single source of truth for the conversation history,
   currently selected language, text direction, and status.
   ================================================================ */

'use strict';

const StateManager = {
  // Key names for persistence
  LANG_STORAGE_KEY: 'clinical_rag_pref_lang',

  state: {
    language: 'en',      // Selected UI language
    direction: 'ltr',    // Text direction (ltr or rtl)
    messages: [],        // Message list: { role: 'user'|'assistant', text: '...', timestamp: Date, metadata: {...} }
    loading: false,      // Whether a request is active
    error: null,         // Error message if any
  },

  listeners: [],

  /**
   * Initialize state from local storage and defaults.
   */
  init() {
    // Restore language preference
    let savedLang = localStorage.getItem(this.LANG_STORAGE_KEY);
    if (!savedLang || !TRANSLATIONS[savedLang]) {
      savedLang = 'en';
    }
    
    this.state.language = savedLang;
    this.state.direction = getLang(savedLang).dir;
    this.state.messages = [];
    this.state.loading = false;
    this.state.error = null;
    
    this.notify();
  },

  /**
   * Register a callback to run whenever the state changes.
   * @param {Function} callback 
   */
  subscribe(callback) {
    this.listeners.push(callback);
  },

  /**
   * Run all subscribed listeners.
   */
  notify() {
    for (const listener of this.listeners) {
      try {
        listener(this.state);
      } catch (err) {
        console.error('State listener error:', err);
      }
    }
  },

  /**
   * Updates the selected UI language and UI text direction.
   * Does NOT alter the message history or active state.
   * @param {string} langCode - The language code (e.g. 'en', 'ar')
   */
  setLanguage(langCode) {
    if (!TRANSLATIONS[langCode]) return;
    
    this.state.language = langCode;
    this.state.direction = getLang(langCode).dir;
    
    // Persist language code in local storage
    localStorage.setItem(this.LANG_STORAGE_KEY, langCode);
    
    this.notify();
  },

  /**
   * Add a new message to the active conversation history.
   * @param {string} role - 'user' or 'assistant'
   * @param {string} text - Message text or recommendation
   * @param {object} [metadata] - API response metadata (evidence, citations, confidence)
   */
  addMessage(role, text, metadata = null) {
    const message = {
      role,
      text,
      timestamp: new Date(),
      metadata: metadata ? {
        evidence: metadata.evidence || '',
        citations: metadata.citations || [],
        confidence: metadata.confidence || 'insufficient'
      } : null
    };
    
    this.state.messages.push(message);
    this.state.error = null; // Clear previous errors on new message
    this.notify();
  },

  /**
   * Clear the active conversation history and error states.
   * Does NOT change the active language or settings.
   */
  clearConversation() {
    this.state.messages = [];
    this.state.error = null;
    this.state.loading = false;
    this.notify();
  },

  /**
   * Set loading status.
   * @param {boolean} isLoading 
   */
  setLoading(isLoading) {
    this.state.loading = isLoading;
    this.notify();
  },

  /**
   * Set error status.
   * @param {string} errorMessage 
   */
  setError(errorMessage) {
    this.state.error = errorMessage;
    this.state.loading = false;
    this.notify();
  }
};

window.StateManager = StateManager;
