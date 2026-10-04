/**
 * MyDoc theme controller — toggle, persistence (localStorage + profile),
 * and OS preference sync. The no-flash inline script lives in <head>.
 */
(function () {
  'use strict';

  const STORAGE_KEY = 'mydoc-theme';

  function currentTheme() {
    return document.documentElement.getAttribute('data-theme') || 'dark';
  }

  function applyTheme(resolved) {
    document.documentElement.setAttribute('data-theme', resolved);
    document.documentElement.style.colorScheme = resolved;
  }

  function resolve(pref) {
    if (pref === 'auto') {
      return window.matchMedia('(prefers-color-scheme: light)').matches
        ? 'light'
        : 'dark';
    }
    return pref === 'light' ? 'light' : 'dark';
  }

  function persist(pref) {
    try {
      if (pref === 'auto') localStorage.removeItem(STORAGE_KEY);
      else localStorage.setItem(STORAGE_KEY, pref);
    } catch (e) { /* storage disabled */ }

    // Logged-in users: remember the choice on the profile too.
    const authenticated = document.documentElement.getAttribute('data-user-theme-default');
    if (authenticated && window.MyDoc && MyDoc.fetchJSON) {
      MyDoc.fetchJSON('/api/me/theme', {
        method: 'POST',
        body: JSON.stringify({ theme: pref }),
      }).catch(() => { /* non-critical */ });
    }
  }

  function toggle() {
    const next = currentTheme() === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    persist(next);
  }

  // Follow the OS when the user preference is "auto".
  window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', () => {
    let stored = null;
    try { stored = localStorage.getItem(STORAGE_KEY); } catch (e) { /* ignore */ }
    const fallback = document.documentElement.getAttribute('data-user-theme-default') || 'auto';
    const pref = stored || fallback;
    if (pref === 'auto') applyTheme(resolve('auto'));
  });

  document.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('theme-toggle');
    if (btn) btn.addEventListener('click', toggle);

    // Reflect flash messages as toasts once components.js is ready.
    document.querySelectorAll('.flash-close').forEach((btn) => {
      btn.addEventListener('click', (e) => e.target.closest('.flash').remove());
    });
  });

  window.MyDocTheme = { toggle, resolve };
})();
