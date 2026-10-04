/**
 * MyDoc API client — thin wrappers around MyDoc.fetchJSON for the
 * endpoints exposed by the /api blueprint.
 */
(function () {
  'use strict';

  const api = {};
  const j = window.MyDoc.fetchJSON;

  // Feed ---------------------------------------------------------------
  api.feed = ({ tab = 'foryou', q = '', page = 1, perPage = 9 } = {}) => {
    const params = new URLSearchParams({ tab, page: String(page), per_page: String(perPage) });
    if (q) params.set('q', q);
    return j(`/api/feed?${params.toString()}`);
  };

  api.tags = (q = '') => j(`/api/tags?q=${encodeURIComponent(q)}`);

  // Documents -----------------------------------------------------------
  api.createDocument = (payload) => j('/api/documents', { method: 'POST', body: JSON.stringify(payload) });
  api.updateDocument = (id, payload) => j(`/api/documents/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
  api.autosave = (id, payload) => j(`/api/documents/${id}/autosave`, { method: 'PUT', body: JSON.stringify(payload) });
  api.deleteDocument = (id) => j(`/api/documents/${id}`, { method: 'DELETE' });
  api.setDocumentStatus = (id, status) =>
    j(`/api/documents/${id}/status`, { method: 'POST', body: JSON.stringify({ status }) });
  api.toggleSave = (id) => j(`/api/documents/${id}/save`, { method: 'POST', body: '{}' });
  api.reportDocument = (id, payload) =>
    j(`/api/documents/${id}/report`, { method: 'POST', body: JSON.stringify(payload) });

  api.uploadCover = async (id, file) => {
    const form = new FormData();
    form.append('cover', file);
    const res = await fetch(`/api/documents/${id}/cover`, {
      method: 'POST',
      headers: { 'X-CSRFToken': window.MyDoc.csrfToken(), Accept: 'application/json' },
      body: form,
    });
    const data = await res.json().catch(() => null);
    if (!res.ok) {
      const err = new Error((data && data.error) || 'Upload failed');
      err.data = data;
      throw err;
    }
    return data;
  };

  // Tickets --------------------------------------------------------------
  api.replyToTicket = (id, body) =>
    j(`/api/tickets/${id}/messages`, { method: 'POST', body: JSON.stringify({ body }) });
  api.getTicketMessages = (id) => j(`/api/tickets/${id}/messages`);

  // Misc -----------------------------------------------------------------
  api.setTheme = (theme) => j('/api/me/theme', { method: 'POST', body: JSON.stringify({ theme }) });
  api.adminStats = () => j('/api/admin/stats');

  window.MyDocAPI = api;
})();
