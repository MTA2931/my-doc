/**
 * Document view page — save/bookmark toggle, report modal,
 * owner publish toggle and delete.
 */
(function () {
  'use strict';

  const { $, $$, escapeHtml } = window.MyDoc;
  const root = $('[data-doc-root]');
  if (!root) return;

  const docId = root.dataset.docId;
  const loggedIn = root.dataset.loggedIn === '1';

  function requireLogin() {
    MyDoc.toast('Please log in to do that.', 'warning');
    setTimeout(() => {
      window.location.href = `/login?next=${encodeURIComponent(window.location.pathname)}`;
    }, 500);
  }

  // ------------------------------------------------------------ Save
  function wireSaveButtons() {
    $$('[data-save-btn]', root).forEach((btn) => {
      btn.addEventListener('click', async () => {
        if (!loggedIn) return requireLogin();
        try {
          const data = await window.MyDocAPI.toggleSave(docId);
          $$('[data-save-btn]', root).forEach((b) => {
            b.setAttribute('aria-pressed', String(data.saved));
            const icon = b.querySelector('[data-save-icon]');
            const label = b.querySelector('[data-save-label]');
            const count = b.querySelector('[data-save-count]');
            if (icon) icon.classList.toggle('icon--filled', data.saved);
            if (label) label.textContent = data.saved ? 'Saved' : 'Save';
            if (count) count.textContent = String(data.count);
          });
          MyDoc.toast(
            data.saved ? 'Added to your saves.' : 'Removed from your saves.',
            'success'
          );
        } catch (err) {
          if (err.status === 401) return requireLogin();
          MyDoc.toast(err.message || 'Could not update save.', 'error');
        }
      });
    });
  }

  // ---------------------------------------------------------- Report
  function wireReportButton() {
    const btn = root.querySelector('[data-report-btn]');
    if (!btn) return;
    btn.addEventListener('click', async () => {
      if (!loggedIn) return requireLogin();

      const bodyHtml = `
        <div class="field">
          <label class="field__label" for="report-reason">Reason</label>
          <select class="input" id="report-reason">
            <option value="spam">Spam</option>
            <option value="plagiarism">Plagiarism</option>
            <option value="harassment">Harassment or hate</option>
            <option value="misinformation">Misinformation</option>
            <option value="other">Something else</option>
          </select>
        </div>
        <div class="field">
          <label class="field__label" for="report-details">Details (optional)</label>
          <textarea class="input textarea" id="report-details" rows="3" maxlength="1000"
                    placeholder="Tell the moderators what's wrong…"></textarea>
        </div>`;

      const confirmed = await MyDoc.openModal({
        title: 'Report this document',
        bodyHtml,
        actions: [
          { label: 'Cancel', variant: 'btn-secondary', value: false },
          { label: 'Submit report', variant: 'btn-danger', value: true },
        ],
      });
      if (!confirmed) return;

      const reason = document.getElementById('report-reason').value;
      const details = document.getElementById('report-details').value;
      try {
        const data = await window.MyDocAPI.reportDocument(docId, { reason, details });
        MyDoc.toast(data.message || 'Report submitted.', 'success');
      } catch (err) {
        MyDoc.toast(err.message || 'Could not submit the report.', 'error');
      }
    });
  }

  // ------------------------------------------------- Owner: status/delete
  function wireOwnerActions() {
    const statusBtn = root.querySelector('[data-status-btn]');
    if (statusBtn) {
      statusBtn.addEventListener('click', async () => {
        const next = statusBtn.dataset.status === 'published' ? 'draft' : 'published';
        statusBtn.classList.add('is-loading');
        try {
          await window.MyDocAPI.setDocumentStatus(docId, next);
          MyDoc.toast(
            next === 'published' ? 'Document published!' : 'Document moved to drafts.',
            'success'
          );
          setTimeout(() => window.location.reload(), 600);
        } catch (err) {
          MyDoc.toast(err.message || 'Could not update status.', 'error');
          statusBtn.classList.remove('is-loading');
        }
      });
    }

    const deleteBtn = root.querySelector('[data-delete-btn]');
    if (deleteBtn) {
      deleteBtn.addEventListener('click', async () => {
        const ok = await MyDoc.confirm(
          'Delete document?',
          '<p>This permanently removes the document, its saves and reports. This action cannot be undone.</p>',
          'Delete forever'
        );
        if (!ok) return;
        deleteBtn.classList.add('is-loading');
        try {
          const data = await window.MyDocAPI.deleteDocument(docId);
          MyDoc.toast('Document deleted.', 'success');
          setTimeout(() => { window.location.href = data.redirect || '/dashboard/documents'; }, 500);
        } catch (err) {
          MyDoc.toast(err.message || 'Could not delete the document.', 'error');
          deleteBtn.classList.remove('is-loading');
        }
      });
    }
  }

  wireSaveButtons();
  wireReportButton();
  wireOwnerActions();
})();
