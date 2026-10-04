/**
 * Home feed — debounced live search, "Load more" pagination with
 * skeleton loaders, all backed by GET /api/feed.
 */
(function () {
  'use strict';

  const { $, $$, escapeHtml, debounce, formatNumber, timeAgo } = window.MyDoc;
  const root = $('[data-feed]');
  if (!root) return;

  const grid = root.querySelector('[data-feed-grid]');
  const skeletons = root.querySelector('[data-feed-skeletons]');
  const empty = root.querySelector('[data-empty]');
  const emptyText = root.querySelector('[data-empty-text]');
  const loadMoreBtn = root.querySelector('[data-load-more]');
  const feedEnd = root.querySelector('[data-feed-end]');
  const searchForm = root.querySelector('[data-feed-search]');
  const searchInput = root.querySelector('[data-feed-input]');

  let state = {
    tab: root.dataset.tab || 'foryou',
    q: root.dataset.q || '',
    page: Number(root.dataset.page || 1),
    loading: false,
  };

  // ---------------------------------------------------------- rendering
  function cardHtml(doc) {
    const cover = doc.cover_image
      ? `<a class="doc-card__cover" href="/doc/${escapeHtml(doc.slug)}" tabindex="-1" aria-hidden="true">
           <img src="/static/${escapeHtml(doc.cover_image)}" alt="" loading="lazy">
         </a>`
      : `<a class="doc-card__cover" href="/doc/${escapeHtml(doc.slug)}" tabindex="-1" aria-hidden="true">
           <div class="doc-card__placeholder" data-initial="${escapeHtml(doc.title.slice(0, 1).toUpperCase())}"></div>
         </a>`;
    const tags = (doc.tags || []).slice(0, 3)
      .map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join('');
    const author = doc.author || {};
    const avatar = author.avatar
      ? `<img class="avatar" src="/static/${escapeHtml(author.avatar)}" alt="" width="26" height="26">`
      : `<span class="avatar avatar--initials" style="--avatar-size: 26px" aria-hidden="true">${escapeHtml((author.display_name || '?').slice(0, 1).toUpperCase())}</span>`;

    return `<article class="doc-card" data-doc-id="${doc.id}">
      ${cover}
      <div class="doc-card__body">
        <div class="doc-card__meta">${tags}
          <span class="doc-card__time">${doc.reading_time} min read</span>
        </div>
        <h3 class="doc-card__title"><a href="/doc/${escapeHtml(doc.slug)}">${escapeHtml(doc.title)}</a></h3>
        <p class="doc-card__summary">${escapeHtml(doc.summary || '')}</p>
        <div class="doc-card__footer">
          ${avatar}
          <span class="doc-card__author">${escapeHtml(author.display_name || '')}</span>
          <span class="doc-card__stats">
            <span title="Views">${formatNumber(doc.views_count)} views</span>
            <span title="Saves">${formatNumber(doc.save_count)} saves</span>
          </span>
        </div>
      </div>
    </article>`;
  }

  function setEmpty(visible, text) {
    if (!empty) return;
    empty.hidden = !visible;
    if (text && emptyText) emptyText.textContent = text;
  }

  function showSkeletons(show) {
    if (skeletons) skeletons.hidden = !show;
  }

  function updateStateUrl() {
    const params = new URLSearchParams();
    if (state.tab !== 'foryou') params.set('tab', state.tab);
    if (state.q) params.set('q', state.q);
    const qs = params.toString();
    history.replaceState(null, '', qs ? `?${qs}` : location.pathname);
  }

  // ------------------------------------------------------------- fetch
  async function fetchFeed({ append = false } = {}) {
    if (state.loading) return;
    state.loading = true;
    if (!append) {
      grid.innerHTML = '';
      showSkeletons(true);
      setEmpty(false);
    } else {
      showSkeletons(true);
      if (loadMoreBtn) loadMoreBtn.classList.add('is-loading');
    }

    try {
      const data = await window.MyDocAPI.feed({
        tab: state.tab,
        q: state.q,
        page: append ? state.page + 1 : 1,
      });
      state.page = data.page;

      if (!append) grid.innerHTML = '';
      const frag = document.createElement('div');
      frag.innerHTML = data.docs.map(cardHtml).join('');
      Array.from(frag.children).forEach((el) => grid.appendChild(el));

      setEmpty(
        data.docs.length === 0 && !append,
        state.q
          ? `Nothing matched “${state.q}”. Try a different keyword.`
          : 'Nothing here yet — be the first to publish something great!'
      );

      const hasMore = Boolean(data.has_more);
      if (loadMoreBtn) loadMoreBtn.hidden = !hasMore;
      if (feedEnd) feedEnd.hidden = hasMore || data.docs.length === 0;
      updateStateUrl();
    } catch (err) {
      MyDoc.toast(err.message || 'Could not load the feed.', 'error');
    } finally {
      state.loading = false;
      showSkeletons(false);
      if (loadMoreBtn) loadMoreBtn.classList.remove('is-loading');
    }
  }

  // --------------------------------------------------------- behaviours
  if (loadMoreBtn) {
    loadMoreBtn.addEventListener('click', () => fetchFeed({ append: true }));
  }

  if (searchInput) {
    searchInput.addEventListener(
      'input',
      debounce(() => {
        state.q = searchInput.value.trim();
        fetchFeed();
      }, 350)
    );
  }

  if (searchForm) {
    searchForm.addEventListener('submit', (e) => {
      e.preventDefault();
      state.q = searchInput.value.trim();
      fetchFeed();
    });
  }

  // Keep hidden field in sync when tabs are clicked (they are plain links).
  $$('.feed-tabs .tab', root).forEach((tabLink) => {
    tabLink.addEventListener('click', () => {
      /* navigation happens; server re-renders with the new tab */
    });
  });

  // Initial empty-state consistency for client-only renders.
  if (grid && !grid.children.length) setEmpty(true);
})();
