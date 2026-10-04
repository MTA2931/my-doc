/**
 * MyDoc auth pages — password strength meter, signup wizard, chip picker.
 */
(function () {
  'use strict';

  const { $, $$ } = window.MyDoc;

  // ------------------------------------------------- Password strength
  function scorePassword(pw) {
    if (!pw) return 0;
    let score = 0;
    if (pw.length >= 8) score += 1;
    if (pw.length >= 12) score += 1;
    if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) score += 1;
    if (/\d/.test(pw) && /[^\w\s]/.test(pw)) score += 1;
    return Math.min(score, 4);
  }

  function initStrengthMeters() {
    $$('input[type="password"][data-strength-target]').forEach((input) => {
      const wrap = input.parentElement.querySelector('[data-strength]');
      if (!wrap) return;
      const bars = $$('.strength__bar', wrap);
      const label = wrap.querySelector('[data-strength-label]');
      const labels = ['Very weak', 'Weak', 'Fair', 'Strong', 'Very strong'];

      input.addEventListener('input', () => {
        const score = scorePassword(input.value);
        wrap.hidden = input.value.length === 0;
        bars.forEach((bar, i) => bar.classList.toggle('is-active', i < score));
        if (label) label.textContent = labels[score];
      });
    });
  }

  // ----------------------------------------------------- Signup wizard
  function initWizard() {
    const root = $('[data-signup-wizard]');
    if (!root) return;

    const panels = $$('[data-step-panel]', root);
    const indicators = $$('[data-step-indicator]', root);
    const summary = root.querySelector('.form-error-summary');
    let current = 1;

    function show(step) {
      current = step;
      panels.forEach((p) => { p.hidden = Number(p.dataset.stepPanel) !== step; });
      indicators.forEach((ind) => {
        const n = Number(ind.dataset.stepIndicator);
        ind.classList.toggle('is-active', n === step);
        ind.classList.toggle('is-done', n < step);
      });
      // Step-1 server errors should be visible on load.
      if (step === 1 && summary) summary.scrollIntoView({ block: 'nearest' });
    }

    // Step 1 client-side checks before advancing.
    const nextBtn = root.querySelector('[data-next-step]');
    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        let ok = true;
        const required = $$('[data-step-panel="1"] [required]', root);
        required.forEach((field) => {
          const invalid = !field.value.trim() ||
            (field.type === 'checkbox' && !field.checked);
          field.setAttribute('aria-invalid', String(invalid));
          if (invalid) ok = false;
        });

        const pw = root.querySelector('input[name="password"]');
        const confirm = root.querySelector('input[name="confirm"]');
        if (pw && confirm && pw.value !== confirm.value) {
          confirm.setAttribute('aria-invalid', 'true');
          MyDoc.toast('Passwords do not match.', 'error');
          ok = false;
        }
        if (ok) show(2);
        else MyDoc.toast('Please complete the highlighted fields.', 'error');
      });
    }

    const prevBtn = root.querySelector('[data-prev-step]');
    if (prevBtn) prevBtn.addEventListener('click', () => show(1));

    // Server-side errors: start on the step owning the first bad field.
    if (summary) {
      show(1);
    }
  }

  // ------------------------------------------------------- Chip picker
  function initChips() {
    const cloud = $('[data-chip-cloud]');
    if (!cloud) return;
    const target = cloud.parentElement.querySelector('[data-chip-target]');
    const countEl = cloud.parentElement.querySelector('[data-chip-count]');
    const selected = new Set();

    // Seed from the input's current value (edit/onboarding flows).
    if (target && target.value) {
      target.value.split(',').forEach((name) => {
        const clean = name.trim().toLowerCase();
        if (clean) selected.add(clean);
      });
    }

    function sync() {
      if (target) target.value = Array.from(selected).join(', ');
      if (countEl) countEl.textContent = String(selected.size);
    }

    $$('[data-chip]', cloud).forEach((chip) => {
      const value = (chip.value || chip.dataset.chip || '').toLowerCase();
      if (selected.has(value)) {
        chip.classList.add('is-selected');
      }
      chip.addEventListener('click', () => {
        if (selected.has(value)) selected.delete(value);
        else selected.add(value);
        chip.classList.toggle('is-selected', selected.has(value));
        chip.setAttribute('aria-pressed', String(selected.has(value)));
        sync();
      });
      chip.setAttribute('aria-pressed', String(selected.has(value)));
    });

    sync();
  }

  document.addEventListener('DOMContentLoaded', () => {
    initStrengthMeters();
    initWizard();
    initChips();
  });
})();
