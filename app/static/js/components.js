/**
 * MyDoc interactive components: dropdowns, modals/confirm dialogs, tabs,
 * mobile navigation, destructive-action confirmation, global inits.
 */
(function () {
  'use strict';

  const { $, $$, on } = window.MyDoc;

  // ------------------------------------------------------ Mobile nav
  function initNavToggle() {
    const toggle = $('#nav-toggle');
    const menu = $('#nav-menu');
    if (!toggle || !menu) return;
    on(toggle, 'click', () => {
      const open = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', String(!open));
      menu.classList.toggle('is-open', !open);
    });
  }

  // --------------------------------------------------------- Dropdowns
  function initDropdowns() {
    const closeAll = (except) => {
      $$('[data-dropdown]').forEach((dd) => {
        if (dd !== except) {
          dd.classList.remove('is-open');
          const t = $('[data-dropdown-toggle]', dd);
          if (t) t.setAttribute('aria-expanded', 'false');
        }
      });
    };

    $$('[data-dropdown]').forEach((dd) => {
      const btn = $('[data-dropdown-toggle]', dd);
      if (!btn) return;
      on(btn, 'click', (e) => {
        e.stopPropagation();
        const open = dd.classList.contains('is-open');
        closeAll(dd);
        dd.classList.toggle('is-open', !open);
        btn.setAttribute('aria-expanded', String(!open));
      });
    });

    on(document, 'click', () => closeAll(null));
    on(document, 'keydown', (e) => {
      if (e.key === 'Escape') closeAll(null);
    });
  }

  // ------------------------------------------------------------ Modal
  let activeModal = null;

  function closeModal() {
    if (!activeModal) return;
    activeModal.classList.remove('is-open');
    const backdrop = activeModal;
    setTimeout(() => backdrop.remove(), 240);
    activeModal = null;
    document.body.style.overflow = '';
  }

  /**
   * Build a modal. `actions` = [{label, variant, value}].
   * Resolves with the chosen action's value, or null when dismissed.
   */
  MyDoc.openModal = ({ title, bodyHtml = '', actions = [] }) =>
    new Promise((resolve) => {
      const backdrop = document.createElement('div');
      backdrop.className = 'modal-backdrop';
      backdrop.setAttribute('role', 'dialog');
      backdrop.setAttribute('aria-modal', 'true');
      backdrop.setAttribute('aria-label', title);

      const modal = document.createElement('div');
      modal.className = 'modal';
      modal.innerHTML =
        `<h2 class="modal__title">${MyDoc.escapeHtml(title)}</h2>` +
        `<div class="modal__body">${bodyHtml}</div>` +
        '<div class="modal__actions"></div>';
      backdrop.appendChild(modal);

      const actionsEl = modal.querySelector('.modal__actions');
      actions.forEach((action) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = `btn ${action.variant || 'btn-secondary'}`;
        btn.textContent = action.label;
        btn.addEventListener('click', () => {
          resolve(action.value);
          closeModal();
        });
        actionsEl.appendChild(btn);
      });

      backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) {
          resolve(null);
          closeModal();
        }
      });
      on(document, 'keydown', function escHandler(e) {
        if (e.key === 'Escape' && activeModal === backdrop) {
          resolve(null);
          closeModal();
          document.removeEventListener('keydown', escHandler);
        }
      });

      document.body.appendChild(backdrop);
      document.body.style.overflow = 'hidden';
      requestAnimationFrame(() => backdrop.classList.add('is-open'));
      activeModal = backdrop;
      const firstBtn = actionsEl.querySelector('button');
      if (firstBtn) firstBtn.focus();
    });

  /** Confirmation dialog for destructive actions. Resolves true/false. */
  MyDoc.confirm = (title, bodyHtml, confirmLabel = 'Confirm') =>
    MyDoc.openModal({
      title,
      bodyHtml,
      actions: [
        { label: 'Cancel', variant: 'btn-secondary', value: false },
        { label: confirmLabel, variant: 'btn-danger', value: true },
      ],
    });

  // ---------------------------------------- data-confirm form intercept
  function initConfirmForms() {
    on(document, 'submit', async (e) => {
      const form = e.target;
      if (!(form instanceof HTMLFormElement) || !form.hasAttribute('data-confirm')) {
        return;
      }
      e.preventDefault();
      const message = form.getAttribute('data-confirm');
      const ok = await MyDoc.confirm('Please confirm', `<p>${message}</p>`, 'Yes, continue');
      if (ok) {
        form.removeAttribute('data-confirm');
        form.requestSubmit();
      }
    });
  }

  // -------------------------------------------------------------- Tabs
  function initTabs() {
    $$('[data-tabs]').forEach((group) => {
      const tabs = $$('[role="tab"]', group);
      tabs.forEach((tab) => {
        on(tab, 'click', () => {
          tabs.forEach((t) => t.setAttribute('aria-selected', 'false'));
          tab.setAttribute('aria-selected', 'true');
          const target = tab.getAttribute('data-tab-target');
          $$('[data-tab-panel]', group.parentElement || document).forEach((panel) => {
            panel.hidden = panel.getAttribute('data-tab-panel') !== target;
          });
        });
      });
    });
  }

  // ---------------------------------------------- Sidebar (mobile)
  function initSidebarToggle() {
    const toggle = $('[data-sidebar-toggle]');
    const sidebar = $('.app-sidebar');
    if (!toggle || !sidebar) return;
    on(toggle, 'click', () => sidebar.classList.toggle('is-open'));
  }

  // ------------------------------------------ Header shadow on scroll
  function initHeaderScroll() {
    const header = $('#site-header');
    if (!header) return;
    const update = () => header.classList.toggle('is-scrolled', window.scrollY > 8);
    update();
    window.addEventListener('scroll', update, { passive: true });
  }

  // ----------------------------------------- Button loading helper
  MyDoc.withLoading = async (btn, fn) => {
    if (!btn) return fn();
    const original = btn.textContent;
    btn.classList.add('is-loading');
    btn.setAttribute('aria-busy', 'true');
    try {
      return await fn();
    } finally {
      btn.classList.remove('is-loading');
      btn.removeAttribute('aria-busy');
      btn.textContent = original;
    }
  };

  document.addEventListener('DOMContentLoaded', () => {
    initNavToggle();
    initDropdowns();
    initConfirmForms();
    initTabs();
    initSidebarToggle();
    initHeaderScroll();
    window.MyDoc.initReveal();
    window.MyDoc.animateCounters();
  });
})();

