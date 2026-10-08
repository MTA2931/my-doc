/**
 * MyDoc Markdown editor — toolbar, live preview, autosave, publish flow.
 */
(function () {
  'use strict';

  const { $, $$, debounce, escapeHtml } = window.MyDoc;
  const root = $('[data-editor]');
  if (!root) return;

  const titleEl = root.querySelector('[data-title]');
  const summaryEl = root.querySelector('[data-summary]');
  const tagsEl = root.querySelector('[data-tags]');
  const slugEl = root.querySelector('[data-slug]');
  const visibilityEl = root.querySelector('[data-visibility]');
  const bodyEl = root.querySelector('[data-body]');
  const previewEl = root.querySelector('[data-preview]');
  const autosaveEl = root.querySelector('[data-autosave-state]');
  const errorsEl = root.querySelector('[data-errors]');
  const countsEl = root.querySelector('[data-counts]');
  const coverInput = root.querySelector('[data-cover]');
  const coverHint = root.querySelector('[data-cover-hint]');

  let docId = root.dataset.docId ? Number(root.dataset.docId) : null;
  let dirty = false;
  let saving = false;

  // ------------------------------------------------------------ helpers
  function payload(status) {
    return {
      title: titleEl.value.trim(),
      summary: summaryEl.value.trim(),
      content_md: bodyEl.value,
      tags: tagsEl.value,
      visibility: visibilityEl.value,
      slug: slugEl.value.trim(),
      status,
    };
  }

  function showErrors(errors) {
    if (!errorsEl) return;
    if (!errors || !Object.keys(errors).length) {
      errorsEl.hidden = true;
      errorsEl.innerHTML = '';
      return;
    }
    const items = Object.entries(errors)
      .map(([field, msgs]) => `<li><strong>${escapeHtml(field)}:</strong> ${msgs.map(escapeHtml).join(' ')}</li>`)
      .join('');
    errorsEl.innerHTML = `<ul>${items}</ul>`;
    errorsEl.hidden = false;
    errorsEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function setSavedState(text) {
    if (autosaveEl) autosaveEl.textContent = text;
  }

  function updateCounts() {
    if (!countsEl) return;
    const words = (bodyEl.value.match(/\b\w+\b/g) || []).length;
    const minutes = Math.max(1, Math.round(words / 200));
    countsEl.textContent = `${words} word${words === 1 ? '' : 's'} · ${minutes} min read`;
  }

  // -------------------------------------------------------- live preview
  function renderPreview() {
    if (!previewEl || !window.MyDocMarkdown) return;
    const md = bodyEl.value;
    if (!md.trim()) {
      previewEl.innerHTML = '<p class="text-muted">Your preview appears here as you type.</p>';
      return;
    }
    previewEl.innerHTML = window.MyDocMarkdown.render(md);
    if (window.MyDocHighlight) {
      window.MyDocHighlight.highlightAll(previewEl);
    }
  }

  // ------------------------------------------------------------ toolbar
  const WRAPPERS = {
    bold: ['**', '**'],
    italic: ['*', '*'],
    strike: ['~~', '~~'],
    code: ['`', '`'],
  };
  const LINE_PREFIX = {
    h2: '## ',
    h3: '### ',
    ul: '- ',
    ol: '1. ',
    task: '- [ ] ',
    quote: '> ',
  };

  function applyToolbar(kind) {
    const start = bodyEl.selectionStart;
    const end = bodyEl.selectionEnd;
    const value = bodyEl.value;
    const selected = value.slice(start, end);

    if (WRAPPERS[kind]) {
      const [before, after] = WRAPPERS[kind];
      bodyEl.setRangeText(before + (selected || 'text') + after, start, end, 'end');
      bodyEl.focus();
    } else if (LINE_PREFIX[kind]) {
      const lineStart = value.lastIndexOf('\n', start - 1) + 1;
      bodyEl.setRangeText(LINE_PREFIX[kind], lineStart, lineStart, 'end');
      bodyEl.focus();
    } else if (kind === 'codeblock') {
      const block = `\n\`\`\`python\n${selected || '# your code here'}\n\`\`\`\n`;
      bodyEl.setRangeText(block, start, end, 'end');
      bodyEl.focus();
    } else if (kind === 'link') {
      const text = selected || 'link text';
      bodyEl.setRangeText(`[${text}](https://example.com)`, start, end, 'end');
      bodyEl.focus();
    } else if (kind === 'image') {
      const alt = selected || 'alt text';
      bodyEl.setRangeText(`![${alt}](/static/uploads/covers/image.png)`, start, end, 'end');
      bodyEl.focus();
    } else if (kind === 'table') {
      const table = '\n| Column 1 | Column 2 |\n| --- | --- |\n| Cell | Cell |\n';
      bodyEl.setRangeText(table, start, end, 'end');
      bodyEl.focus();
    } else if (kind === 'hr') {
      bodyEl.setRangeText('\n---\n', start, end, 'end');
      bodyEl.focus();
    }

    onBodyChanged();
  }

  const toolbar = root.querySelector('[data-toolbar]');
  if (toolbar) {
    toolbar.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-md]');
      if (btn) applyToolbar(btn.dataset.md);
    });
  }

  // ----------------------------------------------------------- autosave
  const autosaveDebounced = debounce(async () => {
    if (!docId || saving || !dirty) return;
    saving = true;
    setSavedState('Saving…');
    try {
      const data = await window.MyDocAPI.autosave(docId, payload(undefined));
      dirty = false;
      setSavedState(`Saved ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`);
      if (data && data.reading_time) updateCounts();
    } catch (err) {
      setSavedState('Autosave failed');
      if (err.status !== 401) MyDoc.toast(err.message || 'Autosave failed.', 'error');
    } finally {
      saving = false;
    }
  }, 1500);

  function onBodyChanged() {
    dirty = true;
    renderPreview();
    updateCounts();
    autosaveDebounced();
  }

  if (bodyEl) bodyEl.addEventListener('input', onBodyChanged);
  [titleEl, summaryEl].forEach((el) => {
    if (el) el.addEventListener('input', () => { dirty = true; autosaveDebounced(); });
  });
  [tagsEl, slugEl, visibilityEl].forEach((el) => {
    if (el) el.addEventListener('change', () => { dirty = true; autosaveDebounced(); });
  });

  // Ctrl/Cmd + S forces a save.
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
      e.preventDefault();
      saveDocument('draft');
    }
  });

  // ------------------------------------------------------- create/update
  async function saveDocument(status) {
    if (saving) return null;
    if (!titleEl.value.trim()) {
      showErrors({ title: ['A title is required.'] });
      titleEl.focus();
      return null;
    }
    if (status === 'published' && !bodyEl.value.trim()) {
      showErrors({ content_md: ['Add some content before publishing.'] });
      bodyEl.focus();
      return null;
    }

    saving = true;
    showErrors(null);
    try {
      let data;
      if (docId) {
        data = await window.MyDocAPI.updateDocument(docId, payload(status));
        applySavedDoc(data.doc);
        setSavedState('Saved');
      } else {
        data = await window.MyDocAPI.createDocument(payload(status));
        docId = data.doc.id;
        applySavedDoc(data.doc);
        root.dataset.docId = String(docId);
        if (coverInput) coverInput.disabled = false;
        if (coverHint) coverHint.textContent = '';
        history.replaceState(null, '', `/doc/${docId}/edit`);
        addViewLink(data.doc.slug);
      }
      dirty = false;
      MyDoc.toast(status === 'published' ? 'Published!' : 'Draft saved.', 'success');
      return data;
    } catch (err) {
      showErrors(err.data && err.data.errors);
      MyDoc.toast(err.message || 'Could not save.', 'error');
      return null;
    } finally {
      saving = false;
    }
  }

  function applySavedDoc(doc) {
    if (!doc) return;
    if (slugEl && doc.slug) slugEl.value = doc.slug;
    root.dataset.docStatus = doc.status;
    const publishBtnNow = root.querySelector('[data-action="publish"]');
    if (publishBtnNow) {
      publishBtnNow.textContent = doc.status === 'published' ? 'Publish changes' : 'Publish';
    }
  }

  function addViewLink(slug) {
    const topbar = root.querySelector('.editor-topbar');
    if (!topbar || topbar.querySelector('[data-view-link]')) return;
    const link = document.createElement('a');
    link.className = 'btn btn-ghost btn-sm';
    link.href = `/doc/${slug}`;
    link.target = '_blank';
    link.rel = 'noopener';
    link.setAttribute('data-view-link', '');
    link.innerHTML =
      'View <svg class="icon" aria-hidden="true" focusable="false">' +
      '<use href="/static/vendor/lucide-sprite.svg#i-arrow-up-right"></use></svg>';
    topbar.insertBefore(link, autosaveEl);
  }

  // ------------------------------------------------------------ actions
  const draftBtn = root.querySelector('[data-action="draft"]');
  const publishBtn = root.querySelector('[data-action="publish"]');
  const deleteBtn = root.querySelector('[data-action="delete"]');

  if (draftBtn) {
    draftBtn.addEventListener('click', () =>
      MyDoc.withLoading(draftBtn, () => saveDocument('draft'))
    );
  }
  if (publishBtn) {
    publishBtn.addEventListener('click', () =>
      MyDoc.withLoading(publishBtn, async () => {
        const data = await saveDocument('published');
        if (data && data.doc && data.doc.status === 'published') {
          setTimeout(() => { window.location.href = `/doc/${data.doc.slug}`; }, 700);
        }
      })
    );
  }
  if (deleteBtn) {
    deleteBtn.addEventListener('click', async () => {
      if (!docId) { window.location.href = '/dashboard/documents'; return; }
      const ok = await MyDoc.confirm(
        'Delete document?',
        '<p>This permanently removes the document. This cannot be undone.</p>',
        'Delete forever'
      );
      if (!ok) return;
      deleteBtn.classList.add('is-loading');
      try {
        await window.MyDocAPI.deleteDocument(docId);
        MyDoc.toast('Document deleted.', 'success');
        setTimeout(() => { window.location.href = '/dashboard/documents'; }, 500);
      } catch (err) {
        MyDoc.toast(err.message || 'Could not delete.', 'error');
        deleteBtn.classList.remove('is-loading');
      }
    });
  }

  // -------------------------------------------------------- cover upload
  if (coverInput) {
    coverInput.addEventListener('change', async () => {
      const file = coverInput.files && coverInput.files[0];
      if (!file) return;
      if (!docId) {
        MyDoc.toast('Save the document first, then upload a cover.', 'warning');
        coverInput.value = '';
        return;
      }
      if (coverHint) coverHint.textContent = 'Uploading…';
      try {
        const data = await window.MyDocAPI.uploadCover(docId, file);
        if (coverHint) coverHint.textContent = `Cover updated: ${data.cover_image}`;
        MyDoc.toast('Cover image uploaded.', 'success');
      } catch (err) {
        if (coverHint) coverHint.textContent = err.message || 'Upload failed.';
        MyDoc.toast(err.message || 'Upload failed.', 'error');
      } finally {
        coverInput.value = '';
      }
    });
  }

  // Warn before losing unsaved changes.
  window.addEventListener('beforeunload', (e) => {
    if (dirty) {
      e.preventDefault();
      e.returnValue = '';
    }
  });

  // Initial render.
  renderPreview();
  updateCounts();
})();


