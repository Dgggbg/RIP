/* ================================================================
   app.js — Main UI Controller and Event Handling
   ----------------------------------------------------------------
   Updates components dynamically on state change, manages DOM events,
   handles inputs, and coordinates i18n/translation application.
   ================================================================ */

'use strict';

document.addEventListener('DOMContentLoaded', () => {
  // ── DOM Cache ──────────────────────────────────────────────────────────────
  const htmlEl = document.documentElement;
  const brandNameEl = document.getElementById('brand-name');
  const brandSubEl = document.getElementById('brand-sub');
  
  const langBtn = document.getElementById('lang-btn');
  const langLabel = document.getElementById('lang-label');
  const langDropdown = document.getElementById('lang-dropdown');
  const langSearch = document.getElementById('lang-search');
  const langList = document.getElementById('lang-list');
  
  const newChatBtn = document.getElementById('new-chat-btn');
  const newChatLabel = document.getElementById('new-chat-label');
  
  const msgList = document.getElementById('msg-list');
  const emptyState = document.getElementById('empty-state');
  const emptyTitle = document.getElementById('empty-title');
  const emptySub = document.getElementById('empty-sub');
  const exampleButtons = [
    document.getElementById('ex-btn-0'),
    document.getElementById('ex-btn-1'),
    document.getElementById('ex-btn-2')
  ];
  
  const chatInput = document.getElementById('chat-input');
  const sendBtn = document.getElementById('send-btn');
  const inputHint = document.getElementById('input-hint');

  let activeSearchQuery = '';

  // ── Initialization ──────────────────────────────────────────────────────────
  StateManager.subscribe(renderUI);
  StateManager.init();
  
  // Build the complete language list once
  rebuildLanguageDropdown();

  // ── State Change Handlers (Reacting to StateManager) ───────────────────────
  function renderUI(state) {
    const lang = state.language;
    const dir = state.direction;

    // 1. Update HTML properties
    htmlEl.setAttribute('lang', lang);
    htmlEl.setAttribute('dir', dir);

    // 2. Localize Static Strings
    brandNameEl.textContent = t('brandName', lang);
    brandSubEl.textContent  = t('brandSub', lang);
    newChatLabel.textContent = t('newChat', lang);
    newChatBtn.setAttribute('aria-label', t('newChat', lang));
    
    // Header Lang Button Update
    const currentLangObj = getLang(lang);
    langLabel.textContent = currentLangObj.nativeName;
    langBtn.setAttribute('aria-label', `${t('searchLang', lang)} - Current: ${currentLangObj.nativeName}`);
    langSearch.placeholder = t('searchLang', lang);

    // Empty Welcome State
    emptyTitle.textContent = t('wTitle', lang);
    emptySub.textContent = t('wSub', lang);
    exampleButtons.forEach((btn, idx) => {
      if (btn) {
        btn.textContent = t(`ex${idx}`, lang);
      }
    });

    // Chat Composer
    chatInput.placeholder = t('placeholder', lang);
    chatInput.setAttribute('aria-label', t('placeholder', lang));
    inputHint.textContent = t('inputHint', lang);
    sendBtn.setAttribute('aria-label', t('send', lang));

    // 3. Render Message Flow
    renderMessages(state);
    
    // 4. Update Inputs Disabled State
    const inputDisabled = state.loading;
    chatInput.disabled = inputDisabled;
    updateSendButtonState();

    // 5. Select active language option in dropdown
    const optButtons = langList.querySelectorAll('.lang-opt');
    optButtons.forEach(btn => {
      const code = btn.getAttribute('data-lang');
      if (code === lang) {
        btn.classList.add('active');
        btn.setAttribute('aria-selected', 'true');
      } else {
        btn.classList.remove('active');
        btn.setAttribute('aria-selected', 'false');
      }
    });
  }

  // ── Render Messages List ───────────────────────────────────────────────────
  function renderMessages(state) {
    // Determine visibility of empty state
    if (state.messages.length === 0) {
      emptyState.style.display = 'flex';
      emptyState.setAttribute('aria-hidden', 'false');
      
      // Remove all elements except emptyState
      Array.from(msgList.children).forEach(child => {
        if (child !== emptyState) child.remove();
      });
      return;
    }

    emptyState.style.display = 'none';
    emptyState.setAttribute('aria-hidden', 'true');

    // Create or update DOM nodes
    const existingMsgCount = msgList.querySelectorAll('.msg-node').length;
    
    // Clear list if user cleared chat or message length differs (re-render)
    if (state.messages.length < existingMsgCount) {
      Array.from(msgList.children).forEach(child => {
        if (child !== emptyState) child.remove();
      });
    }

    const startIdx = msgList.querySelectorAll('.msg-node').length;

    for (let i = startIdx; i < state.messages.length; i++) {
      const msg = state.messages[i];
      const node = createMessageNode(msg, state.language);
      msgList.appendChild(node);
    }

    // Append / Remove loading indicator
    let loadingNode = document.getElementById('loading-indicator');
    if (state.loading) {
      if (!loadingNode) {
        loadingNode = createLoadingNode(state.language);
        msgList.appendChild(loadingNode);
      }
    } else if (loadingNode) {
      loadingNode.remove();
    }

    // Append / Remove error block
    let errorNode = document.getElementById('error-indicator');
    if (state.error) {
      if (!errorNode) {
        errorNode = createErrorNode(state.error);
        msgList.appendChild(errorNode);
      }
    } else if (errorNode) {
      errorNode.remove();
    }

    // Auto-scroll logic
    scrollToBottom();
  }

  // ── Helper: Message Node Builders ──────────────────────────────────────────
  function createMessageNode(msg, currentLang) {
    const wrap = document.createElement('div');
    wrap.className = 'msg-wrap msg-node';
    
    const timeStr = msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    if (msg.role === 'user') {
      wrap.classList.add('user-msg');
      wrap.innerHTML = `
        <div class="user-bubble" dir="auto">${escapeHtml(msg.text)}</div>
        <div class="msg-time">${timeStr}</div>
      `;
    } else {
      wrap.classList.add('asst-msg');
      
      const meta = msg.metadata || {};
      const isRefusal = meta.confidence === 'insufficient';

      let innerContent = '';
      
      if (isRefusal) {
        const isSystemError = msg.text && (msg.text.includes('API_KEY') || msg.text.includes('package') || msg.text.includes('missing') || msg.text.includes('failed') || msg.text.includes('Error') || msg.text.includes('API key'));
        const displayMsg = isSystemError ? msg.text : t('insufficientMsg', currentLang);

        innerContent = `
          <div class="insuf-card">
            <div class="insuf-head">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="err-icon">
                <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              <div class="insuf-title">${t('insufficient', currentLang)}</div>
            </div>
            <div class="insuf-msg">${escapeHtml(displayMsg)}</div>
          </div>
        `;
      } else {
        // Build confidence classes and values
        const confVal = meta.confidence.toLowerCase();
        let badgeClass = 'conf-high';
        let confLabel = t('confHigh', currentLang);

        if (confVal === 'medium') {
          badgeClass = 'conf-medium';
          confLabel = t('confMed', currentLang);
        } else if (confVal === 'low') {
          badgeClass = 'conf-low';
          confLabel = t('confLow', currentLang);
        } else if (confVal === 'insufficient') {
          badgeClass = 'conf-insuf';
          confLabel = t('confInsuf', currentLang);
        }

        // Citations Builder
        let citationsHtml = '';
        if (meta.citations && meta.citations.length > 0) {
          citationsHtml = `
            <div class="card-sec">
              <div class="sec-label">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20M4 19.5A2.5 2.5 0 0 0 6.5 22H20M4 19.5L4 4.5A2.5 2.5 0 0 1 6.5 2L20 2v20H6.5A2.5 2.5 0 0 1 4 19.5z"/>
                </svg>
                <span>${t('sources', currentLang)}</span>
              </div>
              <div class="cit-list">
                ${meta.citations.map((c, i) => `
                  <div class="cit-item">
                    <div class="cit-doc">${escapeHtml(c.document)}</div>
                    <div class="cit-meta">
                      <span class="cit-meta-item"><b>${t('page', currentLang)}:</b> ${c.page}</span>
                      <span class="cit-meta-item"><b>${t('section', currentLang)}:</b> ${escapeHtml(c.section)}</span>
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>
          `;
        }

        // Evidence Builder
        let evidenceHtml = '';
        if (meta.evidence) {
          evidenceHtml = `
            <div class="card-sec">
              <div class="sec-label">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <path d="M3 18v-6a9 9 0 0 1 18 0v6M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3M3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3"/>
                </svg>
                <span>${t('evidence', currentLang)}</span>
              </div>
              <div class="evid-block">"${escapeHtml(meta.evidence)}"</div>
            </div>
          `;
        }

        innerContent = `
          <div class="asst-card">
            <!-- Confidence Banner -->
            <div class="conf-bar">
              <span class="conf-label-text">${t('confidence', currentLang)}:</span>
              <span class="conf-badge ${badgeClass}">${confLabel}</span>
            </div>
            
            <!-- Answer Recommendation -->
            <div class="card-sec">
              <div class="sec-label">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
                <span>${t('answer', currentLang)}</span>
              </div>
              <div class="answer-text">${escapeHtml(msg.text)}</div>
            </div>
            
            <!-- Evidence section -->
            ${evidenceHtml}
            
            <!-- Citations section -->
            ${citationsHtml}
          </div>
        `;
      }

      wrap.innerHTML = `
        <div class="asst-byline">
          <div class="asst-avatar" aria-hidden="true">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#0ea5e9" stroke-width="2.5">
              <rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 12h6M12 9v6"/>
            </svg>
          </div>
          <span class="asst-name">${t('aiLabel', currentLang)}</span>
        </div>
        ${innerContent}
        <div class="msg-time">${timeStr}</div>
      `;
    }

    return wrap;
  }

  function createLoadingNode(currentLang) {
    const wrap = document.createElement('div');
    wrap.className = 'loading-wrap';
    wrap.id = 'loading-indicator';
    wrap.innerHTML = `
      <div class="typing" aria-live="polite">
        <div class="dot"></div>
        <div class="dot"></div>
        <div class="dot"></div>
      </div>
      <span class="loading-txt">${t('loading', currentLang)}</span>
    `;
    return wrap;
  }

  function createErrorNode(errMsgKey) {
    const wrap = document.createElement('div');
    wrap.className = 'err-wrap';
    wrap.id = 'error-indicator';
    
    // Resolve localized error string
    const lang = StateManager.state.language;
    let resolvedErr = t(errMsgKey, lang);
    if (resolvedErr === errMsgKey) {
      resolvedErr = errMsgKey; // Fallback to raw if not localized
    }

    wrap.innerHTML = `
      <div class="err-card" role="alert">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="err-icon" aria-hidden="true">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
        <span class="err-txt">${escapeHtml(resolvedErr)}</span>
      </div>
    `;
    return wrap;
  }

  // ── Keyboard & Input Logic ─────────────────────────────────────────────────
  function handleSendMessage() {
    if (StateManager.state.loading) return;
    
    const question = chatInput.value.trim();
    if (!question) return;

    // Reset composer input height
    chatInput.value = '';
    chatInput.style.height = 'auto';

    // 1. Add User query message to State flow
    StateManager.addMessage('user', question);
    StateManager.setLoading(true);

    // 2. Call RAG endpoint via ApiService
    ApiService.sendQuery(question)
      .then(response => {
        // Parse results safely
        const recommendation = response.recommendation || '';
        StateManager.addMessage('assistant', recommendation, response);
      })
      .catch(err => {
        console.error(err);
        // Translate error key appropriately
        if (err.message.includes('fetch') || err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
          StateManager.setError('errNetwork');
        } else {
          StateManager.setError('errServer');
        }
      })
      .finally(() => {
        StateManager.setLoading(false);
      });
  }

  // Auto-resize chat input text-area
  chatInput.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = (chatInput.scrollHeight) + 'px';
    updateSendButtonState();
  });

  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  });

  sendBtn.addEventListener('click', handleSendMessage);
  
  newChatBtn.addEventListener('click', () => {
    StateManager.clearConversation();
  });

  // Example prompts listener
  exampleButtons.forEach((btn, idx) => {
    if (btn) {
      btn.addEventListener('click', () => {
        const textVal = btn.textContent;
        // Strip the dot mark at start if present
        const questionText = textVal.startsWith('• ') ? textVal.substring(2) : textVal;
        chatInput.value = questionText;
        chatInput.dispatchEvent(new Event('input')); // resize
        chatInput.focus();
      });
    }
  });

  // ── Language Dropdown Controller ──────────────────────────────────────────
  langBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const expanded = langBtn.getAttribute('aria-expanded') === 'true';
    toggleDropdown(!expanded);
  });

  function toggleDropdown(open) {
    if (open) {
      langDropdown.removeAttribute('hidden');
      langBtn.setAttribute('aria-expanded', 'true');
      langSearch.focus();
      activeSearchQuery = '';
      langSearch.value = '';
      filterLanguages();
    } else {
      langDropdown.setAttribute('hidden', '');
      langBtn.setAttribute('aria-expanded', 'false');
    }
  }

  // Close dropdown on outside click
  document.addEventListener('click', (e) => {
    if (!langDropdown.contains(e.target) && e.target !== langBtn) {
      toggleDropdown(false);
    }
  });

  // Search input handler
  langSearch.addEventListener('input', (e) => {
    activeSearchQuery = e.target.value.toLowerCase().trim();
    filterLanguages();
  });

  function rebuildLanguageDropdown() {
    langList.innerHTML = '';
    
    LANGUAGES.forEach(lang => {
      const li = document.createElement('li');
      li.setAttribute('role', 'none');
      
      const btn = document.createElement('button');
      btn.className = 'lang-opt';
      btn.setAttribute('role', 'option');
      btn.setAttribute('data-lang', lang.code);
      btn.setAttribute('aria-selected', 'false');
      btn.innerHTML = `
        <span>${escapeHtml(lang.nativeName)}</span>
        <svg class="lang-check" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
      `;

      btn.addEventListener('click', () => {
        StateManager.setLanguage(lang.code);
        toggleDropdown(false);
      });

      li.appendChild(btn);
      langList.appendChild(li);
    });
  }

  function filterLanguages() {
    const listItems = langList.querySelectorAll('li');
    let matchesCount = 0;

    listItems.forEach(li => {
      const btn = li.querySelector('.lang-opt');
      const code = btn.getAttribute('data-lang');
      const meta = getLang(code);
      
      const native = meta.nativeName.toLowerCase();
      const english = meta.englishName.toLowerCase();
      
      if (native.includes(activeSearchQuery) || english.includes(activeSearchQuery)) {
        li.style.display = 'block';
        matchesCount++;
      } else {
        li.style.display = 'none';
      }
    });

    // Handle empty search state
    let emptySearchMsg = document.getElementById('lang-search-empty');
    if (matchesCount === 0) {
      if (!emptySearchMsg) {
        emptySearchMsg = document.createElement('div');
        emptySearchMsg.id = 'lang-search-empty';
        emptySearchMsg.className = 'lang-none';
        langList.parentElement.appendChild(emptySearchMsg);
      }
      emptySearchMsg.textContent = t('noLang', StateManager.state.language);
      emptySearchMsg.style.display = 'block';
    } else if (emptySearchMsg) {
      emptySearchMsg.style.display = 'none';
    }
  }

  // ── DOM Helpers ────────────────────────────────────────────────────────────
  function updateSendButtonState() {
    const disabled = chatInput.value.trim().length === 0 || StateManager.state.loading;
    sendBtn.disabled = disabled;
  }

  function scrollToBottom() {
    setTimeout(() => {
      msgList.scrollTop = msgList.scrollHeight;
    }, 10);
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
});
