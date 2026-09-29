(function () {
  'use strict';

  function qs(sel) {
    return document.querySelector(sel);
  }

  function isValidEmail(email) {
    const s = String(email || '').trim();
    return /^\S+@\S+\.\S+$/.test(s);
  }

  function waitForFeedbackApi(timeoutMs) {
    const start = Date.now();
    return new Promise((resolve) => {
      (function tick() {
        if (window.SmartCaptchaFeedback && typeof window.SmartCaptchaFeedback.submit === 'function') {
          resolve(window.SmartCaptchaFeedback);
          return;
        }
        if (Date.now() - start >= timeoutMs) {
          resolve(null);
          return;
        }
        window.setTimeout(tick, 50);
      })();
    });
  }

  function init() {
    const trigger = document.getElementById('smartcaptcha-feedback');
    const modal = document.getElementById('sc-feedback-modal');
    const form = document.getElementById('sc-feedback-form');
    const emailEl = document.getElementById('sc-feedback-email');
    const messageEl = document.getElementById('sc-feedback-message');
    const statusEl = document.getElementById('sc-feedback-status');
    const submitBtn = document.getElementById('sc-feedback-submit');

    if (!trigger || !modal || !form || !emailEl || !messageEl || !statusEl || !submitBtn) return;

    let isOpen = false;

    function setStatus(text) {
      statusEl.textContent = text || '';
    }

    function open() {
      if (isOpen) return;
      isOpen = true;
      modal.hidden = false;
      setStatus('');
      window.setTimeout(() => {
        try { emailEl.focus(); } catch (_) {}
      }, 0);
    }

    function close() {
      if (!isOpen) return;
      isOpen = false;
      modal.hidden = true;
      setStatus('');
      form.reset();
      submitBtn.disabled = false;
    }

    trigger.addEventListener('click', (e) => {
      e.preventDefault();
      open();
    });

    modal.addEventListener('click', (e) => {
      const t = e.target;
      if (t && t.getAttribute && t.getAttribute('data-sc-close') === 'true') {
        e.preventDefault();
        close();
      }
    });

    window.addEventListener('keydown', (e) => {
      if (!isOpen) return;
      if (e.key === 'Escape') {
        e.preventDefault();
        close();
      }
    }, { passive: false });

    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      const email = String(emailEl.value || '').trim();
      const message = String(messageEl.value || '').trim();

      if (!isValidEmail(email)) {
        setStatus('Enter a valid email.');
        try { emailEl.focus(); } catch (_) {}
        return;
      }

      submitBtn.disabled = true;
      setStatus('Sending...');

      try {
        const api = await waitForFeedbackApi(2000);
        if (!api) {
          setStatus('Feedback service unavailable.');
          submitBtn.disabled = false;
          return;
        }

        const res = await api.submit(email, message);
        if (res && res.ok) {
          setStatus('Sent. Thank you!');
          window.setTimeout(() => close(), 650);
          return;
        }

        setStatus('Failed to send. Try again later.');
        submitBtn.disabled = false;
      } catch (_) {
        setStatus('Failed to send. Try again later.');
        submitBtn.disabled = false;
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
