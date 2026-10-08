/**
 * MyDoc core helpers — DOM utilities, fetch wrapper with CSRF, toasts.
 * Dependency-free ES6+ module attached to window.MyDoc.
 */
(function () {
  'use strict';

  const MyDoc = {};

  // ------------------------------------------------------------------ DOM
  MyDoc.$ = (sel, ctx) => (ctx || document).querySelector(sel);
  MyDoc.$$ = (sel, ctx) => Array.from((ctx || document).querySelectorAll(sel));

  MyDoc.on = (el, event, handler, opts) => {
    if (el) el.addEventListener(event, handler, opts);
    return () => el && el.removeEventListener(event, handler, opts);
  };

  MyDoc.debounce = (fn, wait = 300) => {
    let timer;
    return function (...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), wait);
    };
  };

  MyDoc.escapeHtml = (value) =>
    String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');

  MyDoc.formatNumber = (n) => {
    n = Number(n) || 0;
    if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, '') + 'M';
    if (n >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, '') + 'k';
    return String(n);
  };

  MyDoc.timeAgo = (iso) => {
    if (!iso) return '';
    const then = new Date(iso);
    if (Number.isNaN(then.getTime())) return '';
    const seconds = Math.max(0, (Date.now() - then.getTime()) / 1000);
    if (seconds < 60) return 'just now';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} hour${hours !== 1 ? 's' : ''} ago`;
    const days = Math.floor(hours / 24);
    if (days < 30) return `${days} day${days !== 1 ? 's' : ''} ago`;
    const months = Math.floor(days / 30);
    if (months < 12) return `${months} month${months !== 1 ? 's' : ''} ago`;
    const years = Math.floor(months / 12);
    return `${years} year${years !== 1 ? 's' : ''} ago`;
  };

  MyDoc.prefersReducedMotion = () =>
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ------------------------------------------------------- CSRF & network
  MyDoc.csrfToken = () => {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  };

  /**
   * fetch() JSON wrapper: adds CSRF header, parses responses, throws
   * structured errors so callers can show field-level messages.
   */
  MyDoc.fetchJSON = async (url, options = {}) => {
    const opts = Object.assign({ headers: {} }, options);
    opts.headers = Object.assign(
      { Accept: 'application/json' },
      opts.headers
    );

    const method = (opts.method || 'GET').toUpperCase();
    if (method !== 'GET' && method !== 'HEAD') {
      opts.headers['X-CSRFToken'] = MyDoc.csrfToken();
      if (opts.body && typeof opts.body === 'string') {
        opts.headers['Content-Type'] = 'application/json';
      }
    }

    const res = await fetch(url, opts);
    let data = null;
    const text = await res.text();
    if (text) {
      try { data = JSON.parse(text); } catch (e) { data = null; }
    }
    if (!res.ok) {
      const error = new Error(
        (data && (data.error || data.message)) || `Request failed (${res.status})`
      );
      error.status = res.status;
      error.data = data;
      throw error;
    }
    return data;
  };

  // ---------------------------------------------------------------- Toasts
  const TOAST_ICONS = {
    success: 'circle-check',
    error: 'circle-x',
    warning: 'triangle-alert',
    info: 'info',
  };

  MyDoc.toast = (message, type = 'info', timeout = 4200) => {
    const region = document.getElementById('toast-region');
    if (!region) return;
    const el = document.createElement('div');
    el.className = `toast toast--${type}`;
    el.setAttribute('role', type === 'error' ? 'alert' : 'status');
    const icon = TOAST_ICONS[type] || TOAST_ICONS.info;
    el.innerHTML =
      `<svg class="icon toast__icon" aria-hidden="true" focusable="false">` +
      `<use href="/static/vendor/lucide-sprite.svg#i-${icon}"></use></svg>` +
      `<span>${MyDoc.escapeHtml(message)}</span>` +
      '<button type="button" class="toast__close" aria-label="Dismiss">&times;</button>';
    region.appendChild(el);

    const remove = () => {
      el.classList.add('is-leaving');
      setTimeout(() => el.remove(), 220);
    };
    el.querySelector('.toast__close').addEventListener('click', remove);
    setTimeout(remove, timeout);
  };

  // --------------------------------------------------- Scroll reveal (IO)
  MyDoc.initReveal = () => {
    const items = MyDoc.$$('.reveal');
    if (!items.length) return;
    if (MyDoc.prefersReducedMotion() || !('IntersectionObserver' in window)) {
      items.forEach((el) => el.classList.add('is-visible'));
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
    );
    items.forEach((el, i) => {
      if (!el.style.getPropertyValue('--reveal-delay')) {
        el.style.setProperty('--reveal-delay', `${Math.min(i % 6, 5) * 70}ms`);
      }
      io.observe(el);
    });
  };

  // -------------------------------------------------- Animated counters
  MyDoc.animateCounters = () => {
    MyDoc.$$('[data-count]').forEach((el) => {
      const target = Number(el.getAttribute('data-count')) || 0;
      if (MyDoc.prefersReducedMotion()) {
        el.textContent = MyDoc.formatNumber(target);
        return;
      }
      const duration = 900;
      const start = performance.now();
      const step = (now) => {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = MyDoc.formatNumber(Math.round(target * eased));
        if (progress < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    });
  };

  window.MyDoc = MyDoc;
})();
