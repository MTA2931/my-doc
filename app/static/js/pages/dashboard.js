/**
 * User dashboard — document table actions, save toggles, ticket replies.
 */
(function () {
  'use strict';

  const { $, $$ } = window.MyDoc;

  // --------------------------------------------- My documents table
  function initDocTable() {
    const table = $('[data-doc-table]');
    if (!table) return;

    $$('[data-status-toggle]', table).forEach((btn) => {
      btn.addEventListener('click', async () => {
        const id = btn.dataset.docId;
        const next = btn.dataset.nextStatus;
        btn.classList.add('is-loading');
        try {
          await window.MyDocAPI.setDocumentStatus(id, next);
          MyDoc.toast(
            next === 'published' ? 'Document published! 🎉' : 'Moved back to drafts.',
            'success'
          );
          setTimeout(() => window.location.reload(), 500);
        } catch (err) {
          MyDoc.toast(err.message || 'Could not update status.', 'error');
          btn.classList.remove('is-loading');
        }
      });
    });

    $$('[data-delete-doc]', table).forEach((btn) => {
      btn.addEventListener('click', async () => {
        const id = btn.dataset.docId;
        const ok = await MyDoc.confirm(
          'Delete document?',
          '<p>This permanently removes the document and all of its saves and reports. This cannot be undone.</p>',
          'Delete forever'
        );
        if (!ok) return;
        btn.classList.add('is-loading');
        try {
          await window.MyDocAPI.deleteDocument(id);
          const row = btn.closest('tr');
          if (row) {
            row.style.transition = 'opacity 200ms';
            row.style.opacity = '0';
            setTimeout(() => row.remove(), 220);
          }
          MyDoc.toast('Document deleted.', 'success');
        } catch (err) {
          MyDoc.toast(err.message || 'Could not delete.', 'error');
          btn.classList.remove('is-loading');
        }
      });
    });
  }

  // -------------------------------------------------- Save toggles
  function initSaveButtons() {
    $$('[data-save-btn]').forEach((btn) => {
      if (btn.closest('[data-doc-root]')) return; // handled by docview.js
      btn.addEventListener('click', async () => {
        const id = btn.dataset.docId;
        try {
          const data = await window.MyDocAPI.toggleSave(id);
          if (!data.saved) {
            const card = btn.closest('.doc-card') || btn.closest('tr');
            if (card) {
              card.style.transition = 'opacity 200ms, transform 200ms';
              card.style.opacity = '0';
              card.style.transform = 'scale(0.98)';
              setTimeout(() => card.remove(), 220);
            }
            MyDoc.toast('Removed from your saves.', 'success');
          } else {
            btn.textContent = '★ Saved';
          }
        } catch (err) {
          MyDoc.toast(err.message || 'Could not update save.', 'error');
        }
      });
    });
  }

  // ------------------------------------------------- Ticket replies
  function initTicketReply() {
    const root = $('[data-ticket-root]');
    const form = $('[data-reply-form]');
    if (!root || !form) return;

    const input = form.querySelector('[data-reply-input]');
    const sendBtn = form.querySelector('[data-reply-send]');

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const body = (input.value || '').trim();
      if (!body) return;

      sendBtn.classList.add('is-loading');
      try {
        const data = await window.MyDocAPI.replyToTicket(root.dataset.ticketId, body);

        // Append the new message to the thread without a reload.
        const article = document.createElement('article');
        article.className = 'thread-msg is-visible';
        article.innerHTML =
          '<header class="thread-msg__head">' +
          '<span class="avatar avatar--initials" style="--avatar-size: 30px">?</span>' +
          '<strong>You</strong>' +
          '<span class="text-xs text-muted">just now</span>' +
          '</header>' +
          `<p class="thread-msg__body"></p>`;
        article.querySelector('.thread-msg__body').textContent = data.message.body;
        form.parentElement.insertBefore(article, form);
        input.value = '';
        MyDoc.toast('Reply sent.', 'success');
      } catch (err) {
        MyDoc.toast(err.message || 'Could not send the reply.', 'error');
      } finally {
        sendBtn.classList.remove('is-loading');
      }
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    initDocTable();
    initSaveButtons();
    initTicketReply();
  });
})();
