(function () {
  'use strict';

  if (window.__SMARTCAPTCHA_FEEDBACK_DISABLED__ === true) return;

  const FIREBASE_SDK_VERSION = '10.7.1';

  const DEFAULT_FIREBASE_CONFIG = {
    apiKey: 'AIzaSy_FIREBASE_API_KEY_PLACEHOLDER',
    authDomain: 'smartcaptcha-feedback.firebaseapp.com',
    projectId: 'smartcaptcha-feedback',
    storageBucket: 'smartcaptcha-feedback.firebasestorage.app',
    messagingSenderId: '838993919490',
    appId: '1:838993919490:web:3e1efefdf73a677d8a311b',
    measurementId: 'G-S5HHWGEDTE'
  };

  const firebaseConfig = (window.__SMARTCAPTCHA_FIREBASE_CONFIG__ && typeof window.__SMARTCAPTCHA_FIREBASE_CONFIG__ === 'object')
    ? window.__SMARTCAPTCHA_FIREBASE_CONFIG__
    : DEFAULT_FIREBASE_CONFIG;

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.async = true;
      s.src = src;
      s.onload = () => resolve();
      s.onerror = () => reject(new Error(`Failed to load script: ${src}`));
      document.head.appendChild(s);
    });
  }

  async function ensureFirebaseCompatLoaded() {
    if (window.firebase && typeof window.firebase.initializeApp === 'function') return;

    const base = `https://www.gstatic.com/firebasejs/${FIREBASE_SDK_VERSION}`;
    await loadScript(`${base}/firebase-app-compat.js`);
    await loadScript(`${base}/firebase-firestore-compat.js`);

    if (!window.firebase || typeof window.firebase.initializeApp !== 'function') {
      throw new Error('Firebase compat SDK not available after load');
    }
  }

  let initPromise = null;

  async function getFirestore() {
    await ensureFirebaseCompatLoaded();

    const existingApps = (window.firebase && typeof window.firebase.apps === 'object') ? window.firebase.apps : [];
    const app = (existingApps && existingApps.length)
      ? existingApps[0]
      : window.firebase.initializeApp(firebaseConfig);

    return window.firebase.firestore(app);
  }

  async function submitFeedback(payload) {
    try {
      const db = await getFirestore();
      await db.collection('feedback').add({
        email: String(payload.email || ''),
        message: payload.message ? String(payload.message) : '',
        createdAt: window.firebase.firestore.FieldValue.serverTimestamp(),
        source: 'smartcaptcha-feedback'
      });
      return { ok: true };
    } catch (err) {
      return { ok: false, error: err };
    }
  }

  window.SmartCaptchaFeedback = {
    init: function init() {
      if (!initPromise) {
        initPromise = Promise.resolve()
          .then(() => true)
          .catch(() => false);
      }
      return initPromise;
    },
    submit: function submit(email, message) {
      return submitFeedback({ email, message });
    }
  };
})();
