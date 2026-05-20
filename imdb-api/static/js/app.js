/* =========================================================
   CineDB — Frontend Application
   ========================================================= */

const API = '';  // same origin
let currentUser = null;
let currentMovieId = null;
let selectedStarRating = 0;
let selectedGenres = [];
let allGenres = [];
let searchOptionsLoaded = false;

// ---- INIT ----
document.addEventListener('DOMContentLoaded', async () => {
  initSession();
  await loadHomePage();
  await navigateToPath(window.location.pathname, false);
  setupPersonAutocomplete('sixDegA');
  setupPersonAutocomplete('sixDegB');
  setupHeroSearchAutocomplete();
});

// Browser back/forward
window.addEventListener('popstate', async (e) => {
  const state = e.state;
  if (!state) { _switchPage('home'); return; }
  if (state.page === 'movie') await openMovie(state.id, false);
  else if (state.page === 'person') await openPerson(state.id, false);
  else _switchPage(state.page);
});

// Intercept all internal <a> clicks — no full reloads
document.addEventListener('click', (e) => {
  const a = e.target.closest('a[href]');
  if (!a) return;
  const href = a.getAttribute('href');
  if (!href || href.startsWith('http') || href.startsWith('mailto')) return;
  // If the SPA contains a matching `#page-<segment>` element, handle
  // the navigation client-side. Otherwise allow the browser to perform
  // a full navigation so server-served pages (e.g. /user) load properly.
  const segment = href.replace(/^\//, '').split('/')[0] || 'home';
  if (!document.getElementById(`page-${segment}`)) {
    // let the browser navigate to server route (no preventDefault)
    return;
  }
  e.preventDefault();
  navigateToPath(href, true);
});

async function navigateToPath(path, push = true) {
  const parts = path.replace(/^\//, '').split('/');
  const [segment, id] = parts;
  if (!segment || segment === 'home') {
    _switchPage('home');
    if (push) history.pushState({page: 'home'}, '', '/');
    else history.replaceState({page: 'home'}, '', '/');
  } else if (segment === 'movie' && id) {
    await openMovie(parseInt(id), push);
  } else if (segment === 'person' && id) {
    await openPerson(parseInt(id), push);
  } else {
    _switchPage(segment);
    if (push) history.pushState({page: segment}, '', `/${segment}`);
    else history.replaceState({page: segment}, '', `/${segment}`);
  }
}

function initSession() {
  try {
    const stored = localStorage.getItem('cinedb_user');
    if (!stored) { window.location.replace('/signin'); return; }
    const user = JSON.parse(stored);
    if (!user || !user.id || !user.username) {
      localStorage.removeItem('cinedb_user');
      window.location.replace('/signin');
      return;
    }
    currentUser = user.id;
    const nameEl = document.getElementById('navUsername');
    if (nameEl) nameEl.textContent = user.username;
  } catch {
    localStorage.removeItem('cinedb_user');
    window.location.replace('/signin');
  }
}

function signOut() {
  localStorage.removeItem('cinedb_user');
  window.location.replace('/signin');
}

// ---- USER DROPDOWN MENU ----
function toggleUserMenu(e) {
  if (e) e.stopPropagation();
  const menu = document.getElementById('userMenu');
  const trigger = document.getElementById('userMenuTrigger');
  if (!menu || !trigger) return;
  const willOpen = menu.classList.contains('hidden');
  menu.classList.toggle('hidden', !willOpen);
  trigger.classList.toggle('open', willOpen);
  trigger.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
}

function closeUserMenu() {
  const menu = document.getElementById('userMenu');
  const trigger = document.getElementById('userMenuTrigger');
  if (!menu || menu.classList.contains('hidden')) return;
  menu.classList.add('hidden');
  if (trigger) {
    trigger.classList.remove('open');
    trigger.setAttribute('aria-expanded', 'false');
  }
}

document.addEventListener('click', (e) => {
  if (!e.target.closest('.nav-user')) closeUserMenu();
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeUserMenu();
});

function setUser(id) {
  currentUser = id ? parseInt(id) : null;
  if (document.getElementById('page-user-dashboard')?.classList.contains('active')) {
    loadUserDashboard();
  }
}

// ---- PAGE ROUTING ----
function _switchPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  const page = document.getElementById(`page-${name}`);
  if (!page) return;
  page.classList.add('active');
  window.scrollTo(0, 0);
  if (name === 'top-rated') loadTopRated();
  if (name === 'trending') loadTrending();
  if (name === 'stats') loadStats();
  if (name === 'people') searchPeople();
  if (name === 'user-dashboard') loadUserDashboard();
  if (name === 'search') loadSearchFilterOptions();
  if (name === 'home' && !cinebotAutoShown) {
    cinebotAutoShown = true;
    setTimeout(() => { if (!cinebotOpen) toggleCinebot(); }, 800);
  }
}

function showPage(name) {
  _switchPage(name);
  history.pushState({page: name}, '', name === 'home' ? '/' : `/${name}`);
}

function goBack() {
  window.history.back();
}

// ---- HOME ----
async function loadHomePage() {
  await Promise.all([
    loadHomeTrending(),
    loadHomeTopRated()
  ]);
}

async function loadHomeTrending() {
  try {
    const movies = await apiFetch('/api/movies/trending');
    renderMovieGrid(document.getElementById('homeTrending'), movies.slice(0, 6));
  } catch (e) {
    document.getElementById('homeTrending').innerHTML = '<p class="loading">Could not load trending</p>';
  }
}

async function loadHomeTopRated() {
  try {
    const movies = await apiFetch('/api/movies/top-rated?limit=6');
    renderMovieGrid(document.getElementById('homeTopRated'), movies.slice(0, 6));
  } catch (e) {
    document.getElementById('homeTopRated').innerHTML = '<p class="loading">Could not load top rated</p>';
  }
}

// ---- MOVIE GRID ----
function renderMovieGrid(container, movies) {
  if (!movies || movies.length === 0) {
    container.innerHTML = '<p class="loading">No movies found.</p>';
    return;
  }
  container.innerHTML = movies.map(m => movieCard(m)).join('');
}

function movieCard(m) {
  const genres = (m.genres || []).slice(0, 2).map(g => `<span class="genre-tag">${g}</span>`).join('');
  const rating = m.average_rating ? m.average_rating.toFixed(1) : '—';
  const poster = m.poster_url
    ? `<img src="${m.poster_url}" alt="${m.title}" loading="lazy" onerror="this.parentElement.innerHTML='🎬'">`
    : '🎬';
  return `
    <div class="movie-card" onclick="openMovie(${m.id})">
      <div class="movie-poster">
        ${poster}
        <span class="movie-cert">${m.certificate || 'U'}</span>
      </div>
      <div class="movie-info">
        <div class="movie-title">${m.title}</div>
        <div class="movie-meta">
          <span>${m.release_year}</span>
          <span class="movie-rating"><span class="star">★</span>${rating}</span>
        </div>
        <div class="genre-tags">${genres}</div>
      </div>
    </div>
  `;
}

// ---- MOVIE DETAIL ----
async function openMovie(movieId, push = true) {
  currentMovieId = movieId;
  _switchPage('movie-detail');
  if (push) history.pushState({page: 'movie', id: movieId}, '', `/movie/${movieId}`);
  const container = document.getElementById('movieDetailContent');
  container.innerHTML = `<div class="loading"><div class="spinner"></div><p>Loading...</p></div>`;

  try {
    const userParam = currentUser ? `?user_id=${currentUser}` : '';
    const [detail, similar, watchlist] = await Promise.all([
      apiFetch(`/api/movies/${movieId}${userParam}`),
      apiFetch(`/api/movies/${movieId}/similar`).catch(() => []),
      currentUser ? apiFetch(`/api/watchlist/${currentUser}`).catch(() => []) : Promise.resolve([])
    ]);
    const inWatchlist = watchlist.some(item => item.movie_id === movieId);
    renderMovieDetail(container, detail, similar, inWatchlist);
  } catch (e) {
    container.innerHTML = `<div class="loading">Failed to load movie details.</div>`;
  }
}

function renderMovieDetail(container, m, similar, inWatchlist = false) {
  const genres = (m.genres || []).map(g => `<span class="genre-tag">${g}</span>`).join('');
  const rating = m.average_rating ? m.average_rating.toFixed(1) : '—';
  const poster = m.poster_url
    ? `<img src="${m.poster_url}" alt="${m.title}" onerror="this.parentElement.innerHTML='🎬'">`
    : '🎬';

  // Rating distribution
  const maxCount = Math.max(...(m.rating_distribution || []).map(r => r.count), 1);
  const distHtml = (m.rating_distribution || []).reverse().map(r => `
    <div class="rating-bar-row">
      <span class="rating-bar-label">${r.score}</span>
      <div class="rating-bar-track">
        <div class="rating-bar-fill" style="width:${Math.round((r.count / maxCount) * 100)}%"></div>
      </div>
      <span class="rating-bar-count">${r.count}</span>
    </div>
  `).join('');

  // Cast & Crew
  let castHtml = '';
  for (const [role, members] of Object.entries(m.cast_and_crew || {})) {
    castHtml += `
      <div class="cast-section">
        <h3>${role}</h3>
        <div class="cast-grid">
          ${members.map(c => `
            <div class="cast-card" onclick="openPerson(${c.person_id})">
              <div class="cast-avatar">👤</div>
              <div class="cast-name">${c.person_name}</div>
              ${c.character_name ? `<div class="cast-char">"${c.character_name}"</div>` : ''}
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  // Reviews
  const renderReview = r => `
    <div class="review-card">
      <div class="review-header">
        <span class="review-user">@${r.username}</span>
        <span class="review-rating">★ ${r.rating}/10</span>
      </div>
      <div class="review-text">${r.text}</div>
      <div class="review-helpful">
        <span id="helpful-count-${r.id}">👍 ${r.helpful_votes} found helpful</span>
        <button
          id="helpful-btn-${r.id}"
          class="helpful-btn${r.user_voted ? ' voted' : ''}"
          onclick="voteHelpful(${r.id}, this)">
          ${r.user_voted ? 'Mark Unhelpful' : 'Mark Helpful'}
        </button>
      </div>
    </div>`;

  let reviewsHtml;
  if (!m.top_reviews || m.top_reviews.length === 0) {
    reviewsHtml = '<p style="color: var(--text-muted)">No reviews yet. Be the first!</p>';
  } else {
    const visible = m.top_reviews.slice(0, 5);
    const hidden  = m.top_reviews.slice(5);
    const extraHtml = hidden.length > 0
      ? `<div id="reviewsExtra-${m.id}" class="hidden">${hidden.map(renderReview).join('')}</div>
         <button class="btn btn-ghost show-more-reviews-btn" onclick="toggleExtraReviews(${m.id}, this)">Show ${hidden.length} More Review${hidden.length !== 1 ? 's' : ''}</button>`
      : '';
    reviewsHtml = `<div class="reviews-scroll-container">${visible.map(renderReview).join('')}${extraHtml}</div>`;
  }

  // Similar movies

  const runtime = m.runtime_minutes ? `${Math.floor(m.runtime_minutes / 60)}h ${m.runtime_minutes % 60}m` : '—';

  container.innerHTML = `
    <button class="back-btn" onclick="goBack()">← Back</button>
    <div class="movie-detail-hero">
      <div class="detail-poster">${poster}</div>
      <div>
        <div class="genre-tags" style="margin-bottom:12px">${genres}</div>
        <h1 class="detail-title">${m.title}</h1>
        <div class="detail-meta-row">
          <div class="detail-meta-item"><span class="label">Year</span>&nbsp;<span class="val">${m.release_year}</span></div>
          <div class="detail-meta-item"><span class="label">Runtime</span>&nbsp;<span class="val">${runtime}</span></div>
          <div class="detail-meta-item"><span class="label">Lang</span>&nbsp;<span class="val">${m.language}</span></div>
          <div class="detail-meta-item"><span class="label">Cert</span>&nbsp;<span class="val">${m.certificate}</span></div>
        </div>
        <div class="big-rating">
          <span class="num">${rating}</span>
          <span class="slash">/</span>
          <span class="denom">10</span>
        </div>
        <div class="rating-vote-count">${m.rating_count} ratings</div>
        <p class="detail-plot">${m.plot_summary || 'No plot summary available.'}</p>
        <div class="detail-actions">
          <button class="btn btn-primary" onclick="openRatingModal(${m.id}, '${m.title.replace(/'/g, "\\'")}')">★ Rate This</button>
          <button class="btn btn-ghost${inWatchlist ? ' in-watchlist' : ''}" id="watchlistBtn-${m.id}" onclick="toggleWatchlist(${m.id})">${inWatchlist ? '✓ In Watchlist' : '+ Watchlist'}</button>
        </div>
      </div>
    </div>

    <div class="two-col">
      <div>
        <h2 style="font-size:1.3rem;margin-bottom:16px;font-family:'Playfair Display',serif">Rating Distribution</h2>
        <div class="rating-dist">${distHtml}</div>
      </div>
      <div>
        <h2 style="font-size:1.3rem;margin-bottom:16px;font-family:'Playfair Display',serif">Top Reviews</h2>
        ${reviewsHtml}
      </div>
    </div>

    <div style="margin-top:40px">
      <h2 style="font-size:1.3rem;margin-bottom:24px;font-family:'Playfair Display',serif">Cast & Crew</h2>
      ${castHtml || '<p style="color:var(--text-muted)">No cast/crew data.</p>'}
    </div>
  `;
}

// ---- TOP RATED ----
async function loadTopRated() {
  const container = document.getElementById('topRatedList');
  container.innerHTML = `<div class="loading"><div class="spinner"></div></div>`;
  try {
    const movies = await apiFetch('/api/movies/top-rated?limit=50');
    if (!movies.length) { container.innerHTML = '<div class="empty-state"><div class="empty-icon">🏆</div><p>No top-rated movies yet (need 10+ ratings).</p></div>'; return; }
    container.innerHTML = movies.map((m, i) => `
      <div class="ranked-item" onclick="openMovie(${m.id})">
        <div class="rank-num ${i < 3 ? 'top3' : ''}">#${i + 1}</div>
        <div class="rank-poster-sm">${m.poster_url ? `<img src="${m.poster_url}" onerror="this.parentElement.innerHTML='🎬'">` : '🎬'}</div>
        <div class="rank-info">
          <div class="rank-title">${m.title}</div>
          <div class="rank-meta">${m.release_year} · ★ ${m.average_rating.toFixed(1)} avg · ${m.rating_count} votes</div>
        </div>
        <div class="rank-score">
          <div class="bayesian-score">${m.bayesian_rating.toFixed(2)}</div>
          <div class="bayesian-label">Bayesian</div>
        </div>
      </div>
    `).join('');
  } catch (e) {
    container.innerHTML = `<div class="loading">Failed to load. Is the API running?</div>`;
  }
}

// ---- TRENDING ----
async function loadTrending() {
  const container = document.getElementById('trendingList');
  container.innerHTML = `<div class="loading"><div class="spinner"></div></div>`;
  try {
    const movies = await apiFetch('/api/movies/trending');
    if (!movies.length) { container.innerHTML = '<div class="empty-state"><div class="empty-icon">🔥</div><p>No trending movies yet.</p></div>'; return; }
    renderMovieGrid(container, movies);
  } catch (e) {
    container.innerHTML = `<div class="loading">Failed to load trending movies.</div>`;
  }
}

// ---- SEARCH ----
function heroSearchGo() {
  const q = document.getElementById('heroSearch').value.trim();
  if (!q) return;
  document.getElementById('filterTitle').value = q;
  showPage('search');
  doSearch();
}

async function doSearch() {
  const title = document.getElementById('filterTitle').value.trim();
  const yearMin = document.getElementById('filterYearMin').value;
  const yearMax = document.getElementById('filterYearMax').value;
  const minRating = document.getElementById('filterMinRating').value;
  const cert = document.getElementById('filterCert').value;
  const lang = document.getElementById('filterLang').value;

  const params = new URLSearchParams();
  if (title) params.append('title', title);
  selectedGenres.forEach(g => params.append('genre', g));
  if (yearMin) params.append('year_min', yearMin);
  if (yearMax) params.append('year_max', yearMax);
  if (minRating) params.append('min_rating', minRating);
  if (cert) params.append('certificate', cert);
  if (lang) params.append('language', lang);
  params.append('limit', '40');

  const container = document.getElementById('searchResults');
  container.innerHTML = `<div class="loading"><div class="spinner"></div></div>`;
  document.getElementById('searchEmpty').classList.add('hidden');

  try {
    const movies = await apiFetch(`/api/movies/search?${params}`);
    if (!movies.length) {
      container.innerHTML = '';
      document.getElementById('searchEmpty').classList.remove('hidden');
      return;
    }
    renderMovieGrid(container, movies);
  } catch (e) {
    container.innerHTML = `<div class="loading">Search failed.</div>`;
  }
}

function clearSearch() {
  ['filterTitle','filterYearMin','filterYearMax','filterMinRating'].forEach(id => {
    document.getElementById(id).value = '';
  });
  document.getElementById('filterCert').value = '';
  document.getElementById('filterLang').value = '';
  document.getElementById('filterGenre').value = '';
  document.getElementById('filterGenre').disabled = false;
  selectedGenres = [];
  renderGenreChips();
  document.getElementById('searchResults').innerHTML = '';
  document.getElementById('searchEmpty').classList.add('hidden');
}

// ---- GENRE / LANGUAGE FILTER ----
async function loadSearchFilterOptions() {
  if (searchOptionsLoaded) return;
  searchOptionsLoaded = true;
  try {
    const [genres, languages] = await Promise.all([
      apiFetch('/api/movies/genres'),
      apiFetch('/api/movies/languages')
    ]);
    allGenres = genres;
    const langSel = document.getElementById('filterLang');
    languages.forEach(l => {
      const opt = document.createElement('option');
      opt.value = l; opt.textContent = l;
      langSel.appendChild(opt);
    });
  } catch (e) {}
  setupGenreAutocomplete();
  setupMovieTitleAutocomplete();
}

function setupGenreAutocomplete() {
  const input = document.getElementById('filterGenre');
  const dropdown = document.getElementById('filterGenre-dropdown');
  if (!input || !dropdown) return;
  input.addEventListener('input', () => {
    const q = input.value.trim().toLowerCase();
    if (!q) { dropdown.classList.add('hidden'); return; }
    const matches = allGenres.filter(g =>
      g.toLowerCase().includes(q) && !selectedGenres.includes(g)
    ).slice(0, 8);
    if (!matches.length) { dropdown.classList.add('hidden'); return; }
    dropdown.innerHTML = matches.map(g =>
      `<div class="autocomplete-item" onclick="addGenreChip('${g.replace(/'/g, "\\'")}')"><span>${g}</span></div>`
    ).join('');
    dropdown.classList.remove('hidden');
  });
  document.addEventListener('click', (e) => {
    if (!input.contains(e.target) && !dropdown.contains(e.target))
      dropdown.classList.add('hidden');
  });
}

function setupMovieTitleAutocomplete() {
  const input = document.getElementById('filterTitle');
  const dropdown = document.getElementById('filterTitle-dropdown');
  if (!input || !dropdown) return;
  let timer;
  input.addEventListener('input', () => {
    clearTimeout(timer);
    const q = input.value.trim();
    if (q.length < 2) { dropdown.classList.add('hidden'); return; }
    timer = setTimeout(async () => {
      try {
        const movies = await apiFetch(`/api/movies/search?title=${encodeURIComponent(q)}&limit=8`);
        if (!movies.length) { dropdown.classList.add('hidden'); return; }
        dropdown.innerHTML = movies.map(m =>
          `<div class="autocomplete-item" onclick="selectTitleSuggestion(${m.id}, '${m.title.replace(/'/g, "\\'")}')">
            <span>${m.title}</span>
            <span class="ac-sub">${m.release_year}${m.genres?.length ? ' · ' + m.genres.slice(0,2).join(', ') : ''}</span>
          </div>`
        ).join('');
        dropdown.classList.remove('hidden');
      } catch { dropdown.classList.add('hidden'); }
    }, 250);
  });
  document.addEventListener('click', (e) => {
    if (!input.contains(e.target) && !dropdown.contains(e.target))
      dropdown.classList.add('hidden');
  });
}

function selectTitleSuggestion(movieId, title) {
  document.getElementById('filterTitle').value = title;
  document.getElementById('filterTitle-dropdown').classList.add('hidden');
  doSearch();
}

function setupHeroSearchAutocomplete() {
  const input = document.getElementById('heroSearch');
  const dropdown = document.getElementById('heroSearch-dropdown');
  if (!input || !dropdown) return;
  let timer;
  input.addEventListener('input', () => {
    clearTimeout(timer);
    const q = input.value.trim();
    if (q.length < 2) { dropdown.classList.add('hidden'); return; }
    timer = setTimeout(async () => {
      try {
        const movies = await apiFetch(`/api/movies/search?title=${encodeURIComponent(q)}&limit=8`);
        if (!movies.length) { dropdown.classList.add('hidden'); return; }
        dropdown.innerHTML = movies.map(m =>
          `<div class="autocomplete-item" onclick="openMovie(${m.id}); document.getElementById('heroSearch-dropdown').classList.add('hidden');">
            <span>${m.title}</span>
            <span class="ac-sub">${m.release_year}${m.genres?.length ? ' · ' + m.genres.slice(0,2).join(', ') : ''}</span>
          </div>`
        ).join('');
        dropdown.classList.remove('hidden');
      } catch { dropdown.classList.add('hidden'); }
    }, 250);
  });
  document.addEventListener('click', (e) => {
    if (!input.contains(e.target) && !dropdown.contains(e.target))
      dropdown.classList.add('hidden');
  });
}

function addGenreChip(genre) {
  if (selectedGenres.includes(genre) || selectedGenres.length >= 3) return;
  selectedGenres.push(genre);
  renderGenreChips();
  const input = document.getElementById('filterGenre');
  input.value = '';
  document.getElementById('filterGenre-dropdown').classList.add('hidden');
  if (selectedGenres.length >= 3) input.disabled = true;
}

function removeGenreChip(genre) {
  selectedGenres = selectedGenres.filter(g => g !== genre);
  renderGenreChips();
  document.getElementById('filterGenre').disabled = false;
}

function renderGenreChips() {
  const container = document.getElementById('genreChips');
  if (!container) return;
  container.innerHTML = selectedGenres.map(g =>
    `<span class="genre-chip">${g}<button class="genre-chip-remove" onclick="removeGenreChip('${g.replace(/'/g, "\\'")}')">×</button></span>`
  ).join('');
}

// ---- PEOPLE ----
async function searchPeople() {
  const name = document.getElementById('personSearch').value.trim();
  const params = new URLSearchParams();
  if (name) params.append('name', name);
  params.append('limit', '40');

  const container = document.getElementById('peopleResults');
  container.innerHTML = `<div class="loading"><div class="spinner"></div></div>`;

  try {
    const people = await apiFetch(`/api/people/search?${params}`);
    if (!people.length) { container.innerHTML = '<div class="empty-state"><div class="empty-icon">👤</div><p>No people found.</p></div>'; return; }
    container.innerHTML = people.map(p => personCard(p)).join('');
  } catch (e) {
    container.innerHTML = `<div class="loading">Failed to load.</div>`;
  }
}

function personCard(p) {
  const photo = p.photo_url
    ? `<img src="${p.photo_url}" alt="${p.name}" onerror="this.parentElement.innerHTML='👤'">`
    : '👤';
  return `
    <div class="person-card" onclick="openPerson(${p.id})">
      <div class="person-avatar">${photo}</div>
      <div class="person-name">${p.name}</div>
      ${p.birth_year ? `<div class="person-birth">Born ${p.birth_year}</div>` : ''}
      <div class="person-id">ID: ${p.id}</div>
    </div>
  `;
}

// ---- PERSON DETAIL ----
async function openPerson(personId, push = true) {
  _switchPage('person-detail');
  if (push) history.pushState({page: 'person', id: personId}, '', `/person/${personId}`);
  const container = document.getElementById('personDetailContent');
  container.innerHTML = `<div class="loading"><div class="spinner"></div></div>`;

  try {
    const [person, filmography, knownFor] = await Promise.all([
      apiFetch(`/api/people/${personId}`),
      apiFetch(`/api/people/${personId}/filmography`),
      apiFetch(`/api/people/${personId}/known-for`)
    ]);
    renderPersonDetail(container, person, filmography, knownFor);
  } catch (e) {
    container.innerHTML = `<div class="loading">Failed to load person details.</div>`;
  }
}

function renderPersonDetail(container, p, filmographyData, knownFor) {
  const photo = p.photo_url
    ? `<img src="${p.photo_url}" alt="${p.name}" onerror="this.parentElement.innerHTML='👤'">`
    : '👤';

  // Known For section
  const knownForHtml = knownFor && knownFor.length > 0
    ? `
        <h2 style="font-size:1.2rem;margin-bottom:14px;font-family:'Playfair Display',serif">Known For</h2>
        <div class="known-for-grid">
          ${knownFor.map(k => `
            <div class="known-card" onclick="openMovie(${k.movie_id})">
              <div class="known-role">${k.role_type}</div>
              <div class="known-title">${k.movie_title}</div>
              <div class="known-year">${k.release_year}</div>
              <div class="known-rating">★ ${k.average_rating.toFixed(1)}</div>
            </div>
          `).join('')}
        </div>
      `
    : '';

  // Filmography
  let filmoHtml = '';
  const fm = filmographyData.filmography || {};
  for (const [role, films] of Object.entries(fm)) {
    filmoHtml += `
      <div class="filmography-section">
        <h3>${role}</h3>
        <div class="filmography-grid">
          ${films.map(f => `
            <div class="film-card" onclick="openMovie(${f.movie_id})">
              <div class="film-title">${f.movie_title}</div>
              <div class="film-year">${f.release_year}</div>
              ${f.character_name ? `<div class="film-char">"${f.character_name}"</div>` : ''}
              <div class="film-rating">★ ${f.average_rating.toFixed(1)}</div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  container.innerHTML = `
    <button class="back-btn" onclick="goBack()">← Back</button>
    <div class="person-detail-hero">
      <div class="person-photo">${photo}</div>
      <div>
        <h1 class="person-detail-name">${p.name}</h1>
        ${p.birth_year ? `<p style="color:var(--text-dim);margin-bottom:12px">Born: ${p.birth_year}</p>` : ''}
        ${p.bio ? `<p class="person-detail-bio">${p.bio}</p>` : ''}
        <div class="person-id-badge">🆔 Person ID: ${p.id}</div>
        <div style="margin-top:12px">
          <button class="btn btn-ghost btn-sm" onclick="prefillSixDegrees(${p.id}, '${p.name.replace(/'/g, "\\'")}')">
            🔗 Six Degrees
          </button>
        </div>
      </div>
    </div>

    ${knownForHtml}

    <h2 style="font-size:1.3rem;margin-bottom:20px;font-family:'Playfair Display',serif">Filmography</h2>
    ${filmoHtml || '<p style="color:var(--text-muted)">No filmography data available.</p>'}
  `;
}

function prefillSixDegrees(personId, personName) {
  const aInput = document.getElementById('sixDegA');
  const bInput = document.getElementById('sixDegB');
  if (!aInput.dataset.personId) {
    aInput.value = personName;
    aInput.dataset.personId = personId;
  } else {
    bInput.value = personName;
    bInput.dataset.personId = personId;
  }
  showPage('six-degrees');
}

// ---- SIX DEGREES ----
async function findSixDegrees() {
  const aInput = document.getElementById('sixDegA');
  const bInput = document.getElementById('sixDegB');
  const a = aInput.dataset.personId;
  const b = bInput.dataset.personId;
  if (!a || !b) { showToast('Select both people from the suggestions', 'error'); return; }

  const container = document.getElementById('sixDegreesResult');
  container.innerHTML = `<div class="loading"><div class="spinner"></div><p>Finding connection...</p></div>`;

  try {
    const result = await apiFetch(`/api/people/six-degrees/${a}/${b}`);
    result._personA = parseInt(a);
    result._personB = parseInt(b);
    renderSixDegreesResult(container, result);
  } catch (e) {
    container.innerHTML = `<div class="loading">Failed to find connection.</div>`;
  }
}

function renderSixDegreesResult(container, result) {
  if (!result.found) {
    container.innerHTML = `
      <div class="not-found">
        <div class="icon">🔗</div>
        <p>No connection found within 6 degrees.</p>
      </div>
    `;
    return;
  }

  const pathHtml = result.path.map((node, i) => {
    const isLast = i === result.path.length - 1;
    return `
      <div class="path-node">
        <div>
          <div class="path-dot">${i === 0 ? '🎬' : isLast ? '🎯' : '👤'}</div>
          ${!isLast ? '<div class="path-line"></div>' : ''}
        </div>
        <div class="path-content">
          <div class="path-name">${node.person_name}</div>
          ${node.connected_via_movie_title
            ? `<div class="path-via">via <strong style="color:var(--gold)">${node.connected_via_movie_title}</strong></div>`
            : ''}
        </div>
      </div>
    `;
  }).join('');

  container.innerHTML = `
    <div class="six-deg-result-header">
      <div class="degrees-badge">
        🔗 ${result.degrees} Degree${result.degrees !== 1 ? 's' : ''} of Separation
      </div>
      <p style="color:var(--text-dim)">Connected through ${result.path.length - 2} intermediate person(s)</p>
    </div>
    <div class="six-deg-path">${pathHtml}</div>
    <div style="margin-top:24px;text-align:center">
      <button class="btn btn-ai" onclick="doAiSixDegreesStory(${result._personA}, ${result._personB})">✦ Tell the Story with AI</button>
    </div>
    <div id="sixDegreesStory" class="mt-4"></div>
  `;
}

// ---- STATS ----
async function loadStats() {
  const container = document.getElementById('statsContent');
  container.innerHTML = `<div class="loading"><div class="spinner"></div></div>`;
  try {
    const s = await apiFetch('/api/stats/');
    container.innerHTML = `
      <div class="stat-card"><div class="stat-icon">🎬</div><div class="stat-num">${s.total_movies}</div><div class="stat-label">Movies</div></div>
      <div class="stat-card"><div class="stat-icon">👤</div><div class="stat-num">${s.total_people}</div><div class="stat-label">People</div></div>
      <div class="stat-card"><div class="stat-icon">👥</div><div class="stat-num">${s.total_users}</div><div class="stat-label">Users</div></div>
      <div class="stat-card"><div class="stat-icon">⭐</div><div class="stat-num">${s.total_ratings}</div><div class="stat-label">Ratings</div></div>
      <div class="stat-card"><div class="stat-icon">📝</div><div class="stat-num">${s.total_reviews}</div><div class="stat-label">Reviews</div></div>
      <div class="stat-card stat-highlight"><div class="stat-icon">📊</div><div class="stat-num">${s.platform_avg_rating}</div><div class="stat-label">Avg Platform Rating</div></div>
      ${s.most_rated_movie ? `<div class="stat-card"><div class="stat-icon">🔥</div><div class="stat-num" style="font-size:1.2rem">${s.most_rated_movie.title}</div><div class="stat-label">Most Rated (${s.most_rated_movie.rating_count} votes)</div></div>` : ''}
      ${s.highest_rated_movie ? `<div class="stat-card stat-highlight"><div class="stat-icon">🏆</div><div class="stat-num" style="font-size:1.2rem">${s.highest_rated_movie.title}</div><div class="stat-label">Highest Rated (★ ${s.highest_rated_movie.average_rating})</div></div>` : ''}
    `;
  } catch (e) {
    container.innerHTML = `<div class="loading">Failed to load stats.</div>`;
  }
}

// ---- RATING / REVIEW MODAL ----
function openRatingModal(movieId, movieTitle, initialRating = 0, initialText = '') {
  if (!currentUser) { showToast('Please select a user first', 'error'); return; }
  currentMovieId = movieId;
  document.getElementById('modalMovieName').textContent = movieTitle;
  document.getElementById('reviewText').value = initialText;
  selectedStarRating = initialRating || 0;
  document.getElementById('selectedRating').textContent = selectedStarRating ? `${selectedStarRating}/10 — ${ratingLabel(selectedStarRating)}` : 'Tap a star to rate';
  renderStars(selectedStarRating);
  document.getElementById('ratingModal').classList.remove('hidden');
}

function closeModal() {
  document.getElementById('ratingModal').classList.add('hidden');
}

function renderStars(selected) {
  const container = document.getElementById('ratingStars');
  container.innerHTML = '';
  for (let i = 1; i <= 10; i++) {
    const btn = document.createElement('button');
    btn.className = `star-btn ${i <= selected ? 'active' : ''}`;
    btn.textContent = '★';
    btn.onclick = () => {
      selectedStarRating = i;
      document.getElementById('selectedRating').textContent = `${i}/10 — ${ratingLabel(i)}`;
      renderStars(i);
    };
    btn.onmouseenter = () => {
      container.querySelectorAll('.star-btn').forEach((b, idx) => {
        b.classList.toggle('hovered', idx < i);
      });
    };
    container.appendChild(btn);
  }
  container.onmouseleave = () => {
    container.querySelectorAll('.star-btn').forEach(b => b.classList.remove('hovered'));
  };
}

function ratingLabel(n) {
  if (n >= 9) return 'Masterpiece';
  if (n >= 8) return 'Excellent';
  if (n >= 7) return 'Good';
  if (n >= 6) return 'Decent';
  if (n >= 5) return 'Average';
  if (n >= 4) return 'Below Average';
  return 'Poor';
}

async function submitRating() {
  if (!selectedStarRating) { showToast('Please select a rating', 'error'); return; }
  const reviewText = document.getElementById('reviewText').value.trim();

  try {
    await apiFetch('/api/ratings/', {
      method: 'POST',
      body: JSON.stringify({ user_id: currentUser, movie_id: currentMovieId, score: selectedStarRating })
    });

    if (reviewText) {
      await apiFetch('/api/reviews/', {
        method: 'POST',
        body: JSON.stringify({ user_id: currentUser, movie_id: currentMovieId, rating: selectedStarRating, text: reviewText })
      });
    }

    closeModal();
    showToast('Rating submitted! ★', 'success');
    if (currentMovieId) openMovie(currentMovieId);
  } catch (e) {
    showToast('Failed to submit rating', 'error');
  }
}

async function voteHelpful(reviewId, btn) {
  if (!currentUser) { showToast('Please select a user first', 'error'); return; }
  if (btn.disabled) return;
  btn.disabled = true;

  try {
    const result = await apiFetch('/api/reviews/helpful', {
      method: 'POST',
      body: JSON.stringify({ review_id: reviewId, user_id: currentUser })
    });

    btn.classList.toggle('voted', result.user_voted);
    btn.textContent = result.user_voted ? 'Mark Unhelpful' : 'Mark Helpful';

    const countEl = document.getElementById(`helpful-count-${reviewId}`);
    if (countEl) countEl.textContent = `👍 ${result.helpful_votes} found helpful`;
  } catch (e) {
    showToast('Failed to update', 'error');
  } finally {
    btn.disabled = false;
  }
}

function toggleExtraReviews(movieId, btn) {
  const extra = document.getElementById(`reviewsExtra-${movieId}`);
  const isHidden = extra.classList.contains('hidden');
  extra.classList.toggle('hidden');
  btn.textContent = isHidden
    ? 'Show Less'
    : `Show ${extra.children.length} More Review${extra.children.length !== 1 ? 's' : ''}`;
}

// ---- WATCHLIST ----
async function toggleWatchlist(movieId) {
  if (!currentUser) { showToast('Please select a user first', 'error'); return; }
  const btn = document.getElementById(`watchlistBtn-${movieId}`);
  const isInWatchlist = btn && btn.classList.contains('in-watchlist');

  try {
    if (isInWatchlist) {
      await apiFetch(`/api/watchlist/${currentUser}/${movieId}`, { method: 'DELETE' });
      showToast('This movie has been removed from the watchlist', '');
      if (btn) {
        btn.textContent = '+ Watchlist';
        btn.classList.remove('in-watchlist');
      }
    } else {
      await apiFetch('/api/watchlist/', {
        method: 'POST',
        body: JSON.stringify({ user_id: currentUser, movie_id: movieId })
      });
      showToast('This movie has been added to the watchlist', 'success');
      if (btn) {
        btn.textContent = '✓ In Watchlist';
        btn.classList.add('in-watchlist');
      }
    }
  } catch (e) {
    showToast('Failed', 'error');
  }
}

// ---- UTILS ----
function debounce(fn, delay) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), delay); };
}

function setupPersonAutocomplete(inputId) {
  const input = document.getElementById(inputId);
  const dropdown = document.getElementById(`${inputId}-dropdown`);

  const fetchSuggestions = debounce(async (query) => {
    if (query.length < 2) { dropdown.classList.add('hidden'); return; }
    try {
      const people = await apiFetch(`/api/people/search?name=${encodeURIComponent(query)}&limit=8`);
      if (!people.length) { dropdown.classList.add('hidden'); return; }
      dropdown.innerHTML = people.map(p =>
        `<div class="autocomplete-item" data-id="${p.id}" data-name="${p.name.replace(/"/g, '&quot;')}">
          ${p.name}${p.birth_year ? `<div class="ac-sub">${p.birth_year}</div>` : ''}
        </div>`
      ).join('');
      dropdown.classList.remove('hidden');
      dropdown.querySelectorAll('.autocomplete-item').forEach(item => {
        item.addEventListener('click', () => {
          input.value = item.dataset.name;
          input.dataset.personId = item.dataset.id;
          dropdown.classList.add('hidden');
        });
      });
    } catch (e) {
      dropdown.classList.add('hidden');
    }
  }, 300);

  input.addEventListener('input', () => {
    delete input.dataset.personId;
    fetchSuggestions(input.value.trim());
  });

  document.addEventListener('click', (e) => {
    if (!input.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.classList.add('hidden');
    }
  });
}

async function apiFetch(url, options = {}) {
  const defaultOpts = {
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' }
  };
  const res = await fetch(`${API}${url}`, { ...defaultOpts, ...options });
  if (!res.ok) {
    const err = new Error(`API error ${res.status}`);
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) return null;
  return res.json();
}

function showToast(msg, type = '') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = `toast ${type}`;
  setTimeout(() => { el.classList.add('hidden'); }, 3000);
}

// Init star buttons with empty state
renderStars(0);

// =====================================================================
// CINEBOT — floating tree-based questionnaire assistant
// =====================================================================

const CINEBOT_TREE = {
  start: {
    msg: "Hi! I'm CineBot 🎬\nWhat can I help you with?",
    options: [
      { label: "🎭 Find by mood",        next: "mood" },
      { label: "🎬 Browse by genre",     next: "genre" },
      { label: "🌍 Browse by language",  next: "language_only" },
      { label: "🏆 Top rated",           action: "top_rated" },
      { label: "🔥 Trending now",        action: "trending" },
      { label: "💎 Hidden gems",         action: "hidden_gems" },
      { label: "🎉 Watch party pick",    next: "party_group" },
      { label: "📋 My watchlist",        action: "watchlist" },
      { label: "📅 Movies by decade",    next: "decade" },
    ]
  },
  mood: {
    msg: "What's your mood tonight?",
    options: [
      { label: "😂 Make me laugh",      set: { genre: "Comedy" },    next: "language" },
      { label: "💪 Action & adrenaline",set: { genre: "Action" },    next: "language" },
      { label: "😢 Let me cry",         set: { genre: "Drama" },     next: "language" },
      { label: "💕 Romantic night",     set: { genre: "Romance" },   next: "language" },
      { label: "😱 Edge of my seat",    set: { genre: "Thriller" },  next: "language" },
      { label: "🌟 Inspire me",         set: { genre: "Biography" }, next: "language" },
      { label: "⚔️ Epic adventure",     set: { genre: "Adventure" }, next: "language" },
      { label: "👨‍👩‍👧 Family fun",         set: { genre: "Family" },   next: "language" },
    ]
  },
  genre: {
    msg: "Pick a genre:",
    options: [
      { label: "Action",    set: { genre: "Action" },    next: "language" },
      { label: "Drama",     set: { genre: "Drama" },     next: "language" },
      { label: "Comedy",    set: { genre: "Comedy" },    next: "language" },
      { label: "Thriller",  set: { genre: "Thriller" },  next: "language" },
      { label: "Romance",   set: { genre: "Romance" },   next: "language" },
      { label: "Biography", set: { genre: "Biography" }, next: "language" },
      { label: "Family",    set: { genre: "Family" },    next: "language" },
      { label: "Crime",     set: { genre: "Crime" },     next: "language" },
      { label: "Sci-Fi",    set: { genre: "Sci-Fi" },    next: "language" },
      { label: "Musical",   set: { genre: "Musical" },   next: "language" },
      { label: "Sport",     set: { genre: "Sport" },     next: "language" },
      { label: "History",   set: { genre: "History" },   next: "language" },
    ]
  },
  language_only: {
    msg: "Which language?",
    options: [
      { label: "🇮🇳 Hindi",   set: { language: "Hindi" },   action: "search_movies" },
      { label: "🎬 Tamil",    set: { language: "Tamil" },   action: "search_movies" },
      { label: "🎭 Telugu",   set: { language: "Telugu" },  action: "search_movies" },
      { label: "🌐 English",  set: { language: "English" }, action: "search_movies" },
      { label: "🌈 Show all", set: {},                      action: "search_movies" },
    ]
  },
  language: {
    msg: "Any language preference?",
    options: [
      { label: "🌈 Any",      set: {},                      action: "search_movies" },
      { label: "🇮🇳 Hindi",   set: { language: "Hindi" },   action: "search_movies" },
      { label: "🎬 Tamil",    set: { language: "Tamil" },   action: "search_movies" },
      { label: "🎭 Telugu",   set: { language: "Telugu" },  action: "search_movies" },
      { label: "🌐 English",  set: { language: "English" }, action: "search_movies" },
    ]
  },
  decade: {
    msg: "Pick a decade:",
    options: [
      { label: "1950s–60s", set: { year_min: 1950, year_max: 1969 }, action: "search_movies" },
      { label: "1970s–80s", set: { year_min: 1970, year_max: 1989 }, action: "search_movies" },
      { label: "1990s",     set: { year_min: 1990, year_max: 1999 }, action: "search_movies" },
      { label: "2000s",     set: { year_min: 2000, year_max: 2009 }, action: "search_movies" },
      { label: "2010s",     set: { year_min: 2010, year_max: 2019 }, action: "search_movies" },
      { label: "2020s",     set: { year_min: 2020, year_max: 2030 }, action: "search_movies" },
    ]
  },
  party_group: {
    msg: "Who are you watching with?",
    options: [
      { label: "🎉 Friends",     set: { group: "friends" }, next: "party_genre" },
      { label: "👨‍👩‍👧 Family",     set: { group: "family" },  next: "party_genre" },
      { label: "💕 Date night",  set: { group: "date" },    next: "party_genre" },
      { label: "👦 Kids night",  set: { group: "kids", certificate: "U" }, action: "party_pick" },
    ]
  },
  party_genre: {
    msg: "What vibe for the group?",
    options: [
      { label: "😂 Funny",       set: { genre: "Comedy" },    action: "party_pick" },
      { label: "💪 Action",      set: { genre: "Action" },    action: "party_pick" },
      { label: "😢 Emotional",   set: { genre: "Drama" },     action: "party_pick" },
      { label: "🌟 Inspiring",   set: { genre: "Biography" }, action: "party_pick" },
      { label: "🎲 Surprise us", set: {},                     action: "party_pick" },
    ]
  },
};

let cinebotOpen = false;
let cinebotCtx  = {};
let cinebotHistory = [];
let cinebotAutoShown = false;

function toggleCinebot() {
  cinebotOpen = !cinebotOpen;
  document.getElementById('cinebotPanel').classList.toggle('hidden', !cinebotOpen);
  if (cinebotOpen && document.getElementById('cinebotMessages').children.length === 0) {
    cinebotReset();
  }
}

function cinebotReset() {
  cinebotCtx = {};
  cinebotHistory = [];
  document.getElementById('cinebotMessages').innerHTML = '';
  cinebotShowNode('start');
}

function cinebotShowNode(nodeId) {
  const node = CINEBOT_TREE[nodeId];
  if (!node) return;
  cinebotBotMsg(node.msg);
  cinebotShowOptions(node.options, nodeId);
}

function cinebotBotMsg(text) {
  const el = document.createElement('div');
  el.className = 'cb-msg cb-bot';
  el.innerHTML = text.replace(/\n/g, '<br>');
  document.getElementById('cinebotMessages').appendChild(el);
  _cbScroll();
}

function cinebotUserMsg(text) {
  const el = document.createElement('div');
  el.className = 'cb-msg cb-user';
  el.textContent = text;
  document.getElementById('cinebotMessages').appendChild(el);
  _cbScroll();
}

function cinebotShowOptions(options, currentNodeId) {
  const wrap = document.createElement('div');
  wrap.className = 'cb-options';
  options.forEach(opt => {
    const btn = document.createElement('button');
    btn.className = 'cb-opt-btn';
    btn.textContent = opt.label;
    btn.onclick = () => {
      wrap.remove();
      cinebotUserMsg(opt.label);
      if (opt.set) Object.assign(cinebotCtx, opt.set);
      if (opt.next) {
        cinebotHistory.push(currentNodeId);
        cinebotShowNode(opt.next);
      } else if (opt.action) {
        cinebotHistory.push(currentNodeId);
        cinebotRunAction(opt.action);
      }
    };
    wrap.appendChild(btn);
  });
  document.getElementById('cinebotMessages').appendChild(wrap);
  _cbScroll();
}

async function cinebotRunAction(action) {
  const loading = document.createElement('div');
  loading.className = 'cb-msg cb-bot';
  loading.innerHTML = '<span class="cb-spinner"></span> Searching...';
  document.getElementById('cinebotMessages').appendChild(loading);
  _cbScroll();

  try {
    let movies = [];
    let headMsg = '';

    if (action === 'top_rated') {
      movies = await apiFetch('/api/movies/top-rated?limit=5');
      headMsg = '🏆 Top rated in CineDB:';
    } else if (action === 'trending') {
      const all = await apiFetch('/api/movies/trending');
      movies = all.slice(0, 5);
      headMsg = '🔥 Trending right now:';
    } else if (action === 'search_movies') {
      const p = new URLSearchParams({ limit: 8 });
      if (cinebotCtx.genre)    p.append('genre', cinebotCtx.genre);
      if (cinebotCtx.language) p.append('language', cinebotCtx.language);
      if (cinebotCtx.year_min) p.append('year_min', cinebotCtx.year_min);
      if (cinebotCtx.year_max) p.append('year_max', cinebotCtx.year_max);
      movies = await apiFetch(`/api/movies/search?${p}`);
      const parts = [];
      if (cinebotCtx.genre)    parts.push(cinebotCtx.genre);
      if (cinebotCtx.language) parts.push(cinebotCtx.language);
      headMsg = `🎬 Top picks${parts.length ? ' — ' + parts.join(', ') : ''}:`;
    } else if (action === 'hidden_gems') {
      const all = await apiFetch('/api/movies/search?min_rating=7&limit=40');
      movies = all.filter(m => (m.rating_count || 0) <= 5)
                  .sort((a, b) => (b.average_rating || 0) - (a.average_rating || 0))
                  .slice(0, 5);
      if (!movies.length) movies = all.slice(-5);
      headMsg = '💎 Hidden gems — great films, few viewers:';
    } else if (action === 'watchlist') {
      if (!currentUser) {
        loading.remove();
        cinebotBotMsg('Please select a user from the top menu first!');
        cinebotShowAgain();
        return;
      }
      const items = await apiFetch(`/api/watchlist/${currentUser}`);
      const fetched = await Promise.all(
        items.slice(0, 5).map(item => apiFetch(`/api/movies/${item.movie_id}`).catch(() => null))
      );
      movies = fetched.filter(Boolean);
      headMsg = movies.length ? '📋 Your watchlist:' : '📋 Your watchlist is empty!';
    } else if (action === 'party_pick') {
      const p = new URLSearchParams({ limit: 20 });
      if (cinebotCtx.genre)       p.append('genre', cinebotCtx.genre);
      if (cinebotCtx.certificate) p.append('certificate', cinebotCtx.certificate);
      const all = await apiFetch(`/api/movies/search?${p}`);
      movies = all.slice(0, 1);
      const groupLabel = { friends:'friends 🎉', family:'family 👨‍👩‍👧', date:'date night 💕', kids:'kids 👦' }[cinebotCtx.group] || 'your group';
      headMsg = movies.length ? `Perfect pick for ${groupLabel}:` : 'No movies found for that combo.';
    }

    loading.remove();

    if (!movies.length) {
      cinebotBotMsg('No movies found for that combo. Try different filters!');
    } else {
      cinebotBotMsg(headMsg);
      movies.forEach(m => cinebotMovieCard(m));
    }
  } catch (e) {
    loading.remove();
    cinebotBotMsg('Oops, something went wrong. Try again!');
  }

  cinebotShowAgain();
}

function cinebotMovieCard(m) {
  const wrap = document.createElement('div');
  wrap.className = 'cb-movie-card';
  wrap.onclick = () => { toggleCinebot(); openMovie(m.id); };
  const rating = (m.average_rating || m.bayesian_rating) ? (m.average_rating || m.bayesian_rating).toFixed(1) : '—';
  const poster = m.poster_url
    ? `<img src="${m.poster_url}" onerror="this.parentElement.innerHTML='🎬'">`
    : '🎬';
  wrap.innerHTML = `
    <div class="cb-card-poster">${poster}</div>
    <div class="cb-card-info">
      <div class="cb-card-title">${m.title}</div>
      <div class="cb-card-meta">${m.release_year || ''} · ★ ${rating}</div>
      <div class="cb-card-lang">${m.language || ''}</div>
    </div>`;
  document.getElementById('cinebotMessages').appendChild(wrap);
  _cbScroll();
}

function cinebotShowAgain() {
  const wrap = document.createElement('div');
  wrap.className = 'cb-options';
  const again = document.createElement('button');
  again.className = 'cb-opt-btn';
  again.textContent = '🔄 Start over';
  again.onclick = cinebotReset;
  wrap.appendChild(again);
  if (cinebotHistory.length > 1) {
    const back = document.createElement('button');
    back.className = 'cb-opt-btn';
    back.textContent = '← Go back';
    back.onclick = () => {
      wrap.remove();
      cinebotCtx = {};
      const prev = cinebotHistory.pop();
      cinebotShowNode(prev);
    };
    wrap.appendChild(back);
  }
  document.getElementById('cinebotMessages').appendChild(wrap);
  _cbScroll();
}

function _cbScroll() {
  const el = document.getElementById('cinebotMessages');
  if (el) el.scrollTop = el.scrollHeight;
}

// Keep showAiTab as no-op so old links don't break
function showAiTab(tab) {
  const tabs = ['chat','mood','search','compare','gems','party','diet','era','insights','dna','recommend'];
  tabs.forEach(t => {
    const panel = document.getElementById(`ai-panel-${t}`);
    const btn   = document.getElementById(`ai-tab-btn-${t}`);
    if (panel) { panel.classList.toggle('hidden', t !== tab); panel.classList.toggle('active', t === tab); }
    if (btn)   btn.classList.toggle('active', t === tab);
  });
}

// ---- AI Smart Search ----
async function doAiSearch() {
  const query = document.getElementById('aiSearchQuery').value.trim();
  if (!query) { showToast('Enter a search query', 'error'); return; }

  const interp = document.getElementById('aiSearchInterpretation');
  const results = document.getElementById('aiSearchResults');
  interp.classList.add('hidden');
  results.innerHTML = `<div class="loading"><div class="spinner"></div><p>AI is thinking...</p></div>`;

  try {
    const data = await apiFetch('/api/ai/search', {
      method: 'POST',
      body: JSON.stringify({ query })
    });

    if (data.interpretation) {
      interp.innerHTML = `
        <div class="ai-interp-box">
          <span class="ai-interp-label">✦ AI understood:</span>
          <span class="ai-interp-text">${data.interpretation}</span>
          ${data.filters_applied && Object.keys(data.filters_applied).length
            ? `<span class="ai-filters-applied">${Object.entries(data.filters_applied).map(([k,v]) => `${k}: <strong>${v}</strong>`).join(' · ')}</span>`
            : ''}
        </div>
      `;
      interp.classList.remove('hidden');
    }

    if (!data.results || data.results.length === 0) {
      results.innerHTML = '<div class="empty-state"><div class="empty-icon">🔍</div><p>No movies matched. Try a different description.</p></div>';
      return;
    }
    renderMovieGrid(results, data.results);
  } catch (e) {
    results.innerHTML = `<div class="loading">${e.message && e.message.includes('503') ? 'AI service not available — set ANTHROPIC_API_KEY' : 'Search failed. Try again.'}</div>`;
  }
}

// ---- AI Insights (from AI page) ----
async function doAiInsights() {
  const movieId = document.getElementById('aiInsightsMovieId').value;
  if (!movieId) { showToast('Enter a movie ID', 'error'); return; }
  const container = document.getElementById('aiInsightsResult');
  container.innerHTML = `<div class="loading"><div class="spinner"></div><p>Analyzing reviews...</p></div>`;
  try {
    const data = await apiFetch(`/api/ai/movies/${movieId}/insights`);
    container.innerHTML = renderInsightsCard(data);
  } catch (e) {
    container.innerHTML = aiErrorHtml(e);
  }
}

// ---- AI Insights (from movie detail page) ----
async function openMovieAiInsights(movieId) {
  const panel = document.getElementById(`movieAiPanel-${movieId}`);
  panel.classList.remove('hidden');
  panel.innerHTML = `<div class="loading"><div class="spinner"></div><p>AI is analyzing reviews...</p></div>`;
  try {
    const data = await apiFetch(`/api/ai/movies/${movieId}/insights`);
    panel.innerHTML = renderInsightsCard(data);
  } catch (e) {
    panel.innerHTML = aiErrorHtml(e);
  }
}

function renderInsightsCard(data) {
  const sentiment = data.sentiment || 'unknown';
  const sentimentClass = sentiment === 'positive' ? 'positive' : sentiment === 'negative' ? 'negative' : 'mixed';
  const sentimentEmoji = sentiment === 'positive' ? '😍' : sentiment === 'negative' ? '😤' : '😐';
  const pros = (data.pros || []).map(p => `<li>✓ ${p}</li>`).join('');
  const cons = (data.cons || []).map(c => `<li>✗ ${c}</li>`).join('');
  return `
    <div class="ai-result-card">
      <div class="ai-result-header">
        <span class="ai-badge">✦ AI Review Synthesis</span>
        <span class="sentiment-badge ${sentimentClass}">${sentimentEmoji} ${sentiment}</span>
      </div>
      <h3 class="ai-movie-title">${data.movie_title}</h3>
      <p class="ai-summary">${data.summary}</p>
      ${data.critic_quote ? `<blockquote class="ai-quote">"${data.critic_quote}"</blockquote>` : ''}
      <div class="ai-pros-cons">
        <div class="ai-pros">
          <h4>Strengths</h4>
          <ul>${pros || '<li>None identified</li>'}</ul>
        </div>
        <div class="ai-cons">
          <h4>Weaknesses</h4>
          <ul>${cons || '<li>None identified</li>'}</ul>
        </div>
      </div>
      <div class="ai-consensus">
        <strong>Verdict:</strong> ${data.consensus}
      </div>
    </div>
  `;
}

// ---- AI DNA (from AI page) ----
async function doAiDna() {
  const movieId = document.getElementById('aiDnaMovieId').value;
  if (!movieId) { showToast('Enter a movie ID', 'error'); return; }
  const container = document.getElementById('aiDnaResult');
  container.innerHTML = `<div class="loading"><div class="spinner"></div><p>Sequencing movie DNA...</p></div>`;
  try {
    const data = await apiFetch(`/api/ai/movies/${movieId}/dna`);
    container.innerHTML = renderDnaCard(data);
  } catch (e) {
    container.innerHTML = aiErrorHtml(e);
  }
}

// ---- AI DNA (from movie detail page) ----
async function openMovieAiDna(movieId) {
  const panel = document.getElementById(`movieAiPanel-${movieId}`);
  panel.classList.remove('hidden');
  panel.innerHTML = `<div class="loading"><div class="spinner"></div><p>Sequencing movie DNA...</p></div>`;
  try {
    const data = await apiFetch(`/api/ai/movies/${movieId}/dna`);
    panel.innerHTML = renderDnaCard(data);
  } catch (e) {
    panel.innerHTML = aiErrorHtml(e);
  }
}

function renderDnaCard(data) {
  const themes = (data.themes || []).map(t => `<span class="dna-tag theme">${t}</span>`).join('');
  const dnaTags = (data.dna_tags || []).map(t => `<span class="dna-tag">${t}</span>`).join('');
  return `
    <div class="ai-result-card dna-card">
      <div class="ai-result-header">
        <span class="ai-badge">🧬 Movie DNA</span>
      </div>
      <h3 class="ai-movie-title">${data.movie_title}</h3>
      <div class="dna-mood">
        <span class="dna-label">Mood</span>
        <span class="dna-value">${data.mood}</span>
      </div>
      <div class="dna-row">
        <span class="dna-label">Themes</span>
        <div class="dna-tags">${themes}</div>
      </div>
      <div class="dna-row">
        <span class="dna-label">Best For</span>
        <p class="dna-text">${data.audience}</p>
      </div>
      <div class="dna-highlight">
        <span class="dna-label">Why Watch Now</span>
        <p class="dna-text highlight">${data.why_watch}</p>
      </div>
      ${data.avoid_if ? `<div class="dna-row"><span class="dna-label">Skip If</span><p class="dna-text muted">${data.avoid_if}</p></div>` : ''}
      <div class="dna-row">
        <span class="dna-label">DNA Tags</span>
        <div class="dna-tags">${dnaTags}</div>
      </div>
    </div>
  `;
}

// ---- AI Recommendations ----
async function doAiRecommend() {
  if (!currentUser) { showToast('Please select a user first', 'error'); return; }
  const container = document.getElementById('aiRecommendResult');
  container.innerHTML = `<div class="loading"><div class="spinner"></div><p>Analyzing your taste profile...</p></div>`;
  try {
    const data = await apiFetch(`/api/ai/users/${currentUser}/recommend`);
    if (!data.taste_profile) {
      container.innerHTML = '<div class="empty-state"><div class="empty-icon">🎯</div><p>Rate some movies first to get personalized recommendations.</p></div>';
      return;
    }
    const recsHtml = (data.recommendations || []).map(r => `
      <div class="rec-card" onclick="openMovie(${r.movie_id})">
        <div class="rec-score">${r.match_score ? r.match_score.toFixed(1) : '—'}</div>
        <div class="rec-content">
          <div class="rec-title">${r.title}</div>
          <div class="rec-genres">${(r.genres || []).join(' · ')}</div>
          <div class="rec-reason">✦ ${r.reason}</div>
          ${r.average_rating ? `<div class="rec-rating">★ ${r.average_rating.toFixed(1)} avg</div>` : ''}
        </div>
      </div>
    `).join('');
    container.innerHTML = `
      <div class="ai-result-card">
        <div class="ai-result-header">
          <span class="ai-badge">✦ Your Taste Profile</span>
          <span style="color:var(--text-dim);font-size:0.85rem">${data.rated_movie_count} movies rated</span>
        </div>
        <p class="ai-taste-profile">${data.taste_profile}</p>
      </div>
      <div class="rec-list">${recsHtml}</div>
    `;
  } catch (e) {
    container.innerHTML = aiErrorHtml(e);
  }
}

// ---- AI Six Degrees Story ----
async function doAiSixDegreesStory(personAId, personBId) {
  const storyContainer = document.getElementById('sixDegreesStory');
  storyContainer.innerHTML = `<div class="loading"><div class="spinner"></div><p>AI is crafting the story...</p></div>`;
  try {
    const data = await apiFetch(`/api/ai/six-degrees/${personAId}/${personBId}/story`);
    storyContainer.innerHTML = `
      <div class="ai-result-card story-card">
        <div class="ai-result-header">
          <span class="ai-badge">✦ The Story</span>
        </div>
        <p class="ai-story-text">${data.story}</p>
        ${data.fun_fact ? `
          <div class="fun-fact-box">
            <span class="fun-fact-label">💡 Fun Fact</span>
            <p>${data.fun_fact}</p>
          </div>
        ` : ''}
      </div>
    `;
  } catch (e) {
    storyContainer.innerHTML = aiErrorHtml(e);
  }
}

// ---- AI Error helper ----
function aiErrorHtml(e) {
  const msg = e.message || '';
  if (msg.includes('503')) {
    return `<div class="ai-result-card"><p style="color:var(--gold)">⚠️ AI requires Ollama running locally.<br><code>ollama serve && ollama pull llama3.1:8b && ollama pull llama3.2:3b</code></p></div>`;
  }
  return `<div class="ai-result-card"><p style="color:var(--text-muted)">AI analysis failed. Please try again.</p></div>`;
}

// =====================================================================
// NEW AI FEATURES
// =====================================================================

// ---- CHATBOT ----
let chatSessionId = null;

async function sendChat() {
  const input = document.getElementById('chatInput');
  const message = input.value.trim();
  if (!message) return;
  input.value = '';

  appendChatMessage('user', message);
  const thinkingEl = appendChatMessage('bot', '...', [], true);

  try {
    const data = await apiFetch('/api/ai/chat', {
      method: 'POST',
      body: JSON.stringify({ message, session_id: chatSessionId, user_id: currentUser || 1 })
    });
    chatSessionId = data.session_id;
    thinkingEl.remove();
    appendChatMessage('bot', data.reply, data.tools_used || []);
  } catch (e) {
    thinkingEl.remove();
    appendChatMessage('bot', 'CineBot is offline. Make sure Ollama is running with llama3.1:8b.');
  }
}

function appendChatMessage(role, text, toolsUsed = [], isThinking = false) {
  const container = document.getElementById('chatMessages');
  const el = document.createElement('div');
  el.className = `chat-message ${role}${isThinking ? ' thinking' : ''}`;

  const bubble = document.createElement('div');
  bubble.className = 'chat-bubble';
  bubble.textContent = text;
  el.appendChild(bubble);

  if (toolsUsed && toolsUsed.length > 0) {
    const tools = document.createElement('div');
    tools.className = 'chat-tools-used';
    tools.textContent = `🔧 ${toolsUsed.map(t => t.tool).join(', ')}`;
    el.appendChild(tools);
  }

  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
  return el;
}

async function clearChatSession() {
  if (chatSessionId) {
    await apiFetch(`/api/ai/chat/${chatSessionId}`, { method: 'DELETE' }).catch(() => {});
    chatSessionId = null;
  }
  document.getElementById('chatMessages').innerHTML = '';
}

// ---- MOOD DISCOVERY ----
async function doMoodSearch() {
  const mood = document.getElementById('moodInput').value.trim();
  if (!mood) { showToast('Describe your mood first', 'error'); return; }

  const interp = document.getElementById('moodInterpretation');
  const results = document.getElementById('moodResults');
  interp.classList.add('hidden');
  results.innerHTML = `<div class="loading"><div class="spinner"></div><p>AI is reading your vibe...</p></div>`;

  try {
    const data = await apiFetch('/api/ai/mood', {
      method: 'POST',
      body: JSON.stringify({ mood })
    });

    if (data.mood_interpretation) {
      interp.innerHTML = `<div class="ai-interp-box"><span class="ai-interp-label">✦ AI reads your vibe:</span><span class="ai-interp-text">${data.mood_interpretation}</span></div>`;
      interp.classList.remove('hidden');
    }

    if (!data.picks || data.picks.length === 0) {
      results.innerHTML = '<div class="empty-state"><div class="empty-icon">🌙</div><p>No movies matched that mood. Try rephrasing.</p></div>';
      return;
    }
    results.innerHTML = data.picks.map(p => moodMovieCard(p)).join('');
  } catch (e) {
    results.innerHTML = aiErrorHtml(e);
  }
}

function moodMovieCard(m) {
  const genres = (m.genres || []).slice(0, 2).map(g => `<span class="genre-tag">${g}</span>`).join('');
  const rating = m.average_rating ? m.average_rating.toFixed(1) : '—';
  const poster = m.poster_url
    ? `<img src="${m.poster_url}" alt="${m.title}" loading="lazy" onerror="this.parentElement.innerHTML='🎬'">`
    : '🎬';
  return `
    <div class="movie-card" onclick="openMovie(${m.id})">
      <div class="movie-poster">${poster}<span class="movie-cert">${m.certificate || 'U'}</span></div>
      <div class="movie-info">
        <div class="movie-title">${m.title}</div>
        <div class="movie-meta"><span>${m.release_year || ''}</span><span class="movie-rating"><span class="star">★</span>${rating}</span></div>
        <div class="genre-tags">${genres}</div>
        ${(m.why_fits_mood || m.why) ? `<div class="mood-why">✦ ${m.why_fits_mood || m.why}</div>` : ''}
      </div>
    </div>`;
}

// ---- MOVIE COMPARE ----
async function doCompare() {
  const a = document.getElementById('compareMovieA').value;
  const b = document.getElementById('compareMovieB').value;
  if (!a || !b) { showToast('Enter both movie IDs', 'error'); return; }

  const container = document.getElementById('compareResult');
  container.innerHTML = `<div class="loading"><div class="spinner"></div><p>AI is analyzing both films...</p></div>`;

  try {
    const data = await apiFetch(`/api/ai/movies/compare?a=${a}&b=${b}`);
    container.innerHTML = renderCompareCard(data);
  } catch (e) {
    container.innerHTML = aiErrorHtml(e);
  }
}

function renderCompareCard(data) {
  const ma = data.movie_a;
  const mb = data.movie_b;
  const posterA = ma.poster_url ? `<img src="${ma.poster_url}" onerror="this.parentElement.innerHTML='🎬'">` : '🎬';
  const posterB = mb.poster_url ? `<img src="${mb.poster_url}" onerror="this.parentElement.innerHTML='🎬'">` : '🎬';
  return `
    <div class="ai-result-card">
      <div class="ai-result-header"><span class="ai-badge">⚖️ AI Comparison</span></div>
      <div class="compare-result-header">
        <div class="compare-movie-thumb" onclick="openMovie(${ma.id})">
          <div class="compare-poster">${posterA}</div>
          <div class="compare-movie-name">${ma.title}</div>
          <div class="compare-movie-rating">★ ${ma.average_rating ? ma.average_rating.toFixed(1) : '—'}</div>
        </div>
        <div class="compare-vs">VS</div>
        <div class="compare-movie-thumb" onclick="openMovie(${mb.id})">
          <div class="compare-poster">${posterB}</div>
          <div class="compare-movie-name">${mb.title}</div>
          <div class="compare-movie-rating">★ ${mb.average_rating ? mb.average_rating.toFixed(1) : '—'}</div>
        </div>
      </div>
      ${data.similarities    ? `<div class="compare-section"><span class="compare-label">What they share</span><p class="compare-text">${Array.isArray(data.similarities) ? data.similarities.join(' · ') : data.similarities}</p></div>` : ''}
      ${data.tone_a          ? `<div class="compare-section"><span class="compare-label">${ma.title} — tone</span><p class="compare-text">${data.tone_a}</p></div>` : ''}
      ${data.tone_b          ? `<div class="compare-section"><span class="compare-label">${mb.title} — tone</span><p class="compare-text">${data.tone_b}</p></div>` : ''}
      ${data.better_for_a    ? `<div class="compare-section"><span class="compare-label">Watch ${ma.title} if...</span><p class="compare-text">${data.better_for_a}</p></div>` : ''}
      ${data.better_for_b    ? `<div class="compare-section"><span class="compare-label">Watch ${mb.title} if...</span><p class="compare-text">${data.better_for_b}</p></div>` : ''}
      ${data.verdict         ? `<div class="ai-consensus"><strong>Verdict:</strong> ${data.verdict}</div>` : ''}
    </div>`;
}

// ---- HIDDEN GEMS ----
async function doHiddenGems() {
  if (!currentUser) { showToast('Please select a user first', 'error'); return; }
  const container = document.getElementById('gemsResult');
  container.innerHTML = `<div class="loading"><div class="spinner"></div><p>Mining for hidden gems...</p></div>`;

  try {
    const data = await apiFetch(`/api/ai/users/${currentUser}/hidden-gems`);
    if (!data.gems || data.gems.length === 0) {
      container.innerHTML = '<div class="empty-state"><div class="empty-icon">💎</div><p>No hidden gems found. Rate more movies to improve suggestions.</p></div>';
      return;
    }
    container.innerHTML = `<div class="rec-list">${data.gems.map(g => gemCard(g)).join('')}</div>`;
  } catch (e) {
    container.innerHTML = aiErrorHtml(e);
  }
}

function gemCard(g) {
  const poster = g.poster_url ? `<img src="${g.poster_url}" onerror="this.parentElement.innerHTML='🎬'">` : '🎬';
  return `
    <div class="rec-card" onclick="openMovie(${g.id})">
      <div class="gem-poster">${poster}</div>
      <div class="rec-content">
        <div class="rec-title">💎 ${g.title}</div>
        <div class="rec-genres">${(g.genres || []).join(' · ')} · ${g.release_year}</div>
        ${(g.gem_reason || g.why_for_you) ? `<div class="rec-reason">✦ ${g.gem_reason || g.why_for_you}</div>` : ''}
        ${g.average_rating ? `<div class="rec-rating">★ ${g.average_rating.toFixed(1)} avg · ${g.rating_count || 0} ratings</div>` : ''}
      </div>
    </div>`;
}

// ---- WATCH PARTY ----
let selectedGroupType = 'friends';

function selectGroup(btn, type) {
  selectedGroupType = type;
  document.querySelectorAll('.group-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

async function doWatchParty() {
  const mood = document.getElementById('partyMood').value.trim();
  const container = document.getElementById('partyResult');
  container.innerHTML = `<div class="loading"><div class="spinner"></div><p>Planning the perfect watch...</p></div>`;

  try {
    const data = await apiFetch('/api/ai/watch-party', {
      method: 'POST',
      body: JSON.stringify({ group_type: selectedGroupType, mood, avoid_genres: [] })
    });
    container.innerHTML = renderPartyResult(data);
  } catch (e) {
    container.innerHTML = aiErrorHtml(e);
  }
}

function renderPartyResult(data) {
  if (!data.pick) return '<div class="empty-state"><div class="empty-icon">🎉</div><p>No movies found for this group.</p></div>';
  const p = data.pick;
  const poster = p.poster_url ? `<img src="${p.poster_url}" onerror="this.parentElement.innerHTML='🎬'">` : '🎬';
  const starters = (p.conversation_starters || []).map(s => `<li>${s}</li>`).join('');
  const runnerUp = data.runner_up ? `
    <div style="margin-top:16px;padding-top:16px;border-top:1px solid var(--border)">
      <span style="color:var(--text-muted);font-size:0.8rem;font-weight:700;text-transform:uppercase">Runner Up</span>
      <div class="runner-up-card" onclick="openMovie(${data.runner_up.id})">
        ${data.runner_up.title} · ${data.runner_up.release_year} · ★ ${data.runner_up.average_rating ? data.runner_up.average_rating.toFixed(1) : '—'}
      </div>
    </div>` : '';
  return `
    <div class="ai-result-card">
      <div class="ai-result-header">
        <span class="ai-badge">🎉 Watch Party Pick</span>
        <span style="color:var(--text-dim);font-size:0.85rem">${data.group_type} night</span>
      </div>
      <div class="party-pick-layout">
        <div class="party-poster" onclick="openMovie(${p.id})">${poster}</div>
        <div class="party-info">
          <div class="party-title" onclick="openMovie(${p.id})">${p.title}</div>
          <div class="party-meta">${p.release_year} · ${p.language} · ★ ${p.average_rating ? p.average_rating.toFixed(1) : '—'}</div>
          <div class="party-genres" style="margin:8px 0">${(p.genres || []).map(g => `<span class="genre-tag">${g}</span>`).join('')}</div>
          ${p.why_perfect ? `<p class="party-why">✦ ${p.why_perfect}</p>` : ''}
          ${starters ? `<div class="party-starters"><div class="starters-label">Conversation Starters</div><ul class="starters-list">${starters}</ul></div>` : ''}
        </div>
      </div>
      ${runnerUp}
    </div>`;
}

// ---- CINEMA DIET (BLIND SPOTS) ----
async function doCinemaDiet() {
  if (!currentUser) { showToast('Please select a user first', 'error'); return; }
  const container = document.getElementById('dietResult');
  container.innerHTML = `<div class="loading"><div class="spinner"></div><p>Auditing your cinema diet...</p></div>`;

  try {
    const data = await apiFetch(`/api/ai/users/${currentUser}/blind-spots`);
    if (!data.blind_spots || data.blind_spots.length === 0) {
      container.innerHTML = `<div class="ai-result-card"><p style="color:var(--green)">✓ ${data.message || 'No major blind spots found — impressive!'}</p></div>`;
      return;
    }
    container.innerHTML = `<div class="rec-list">${data.blind_spots.map(bs => dietCard(bs)).join('')}</div>`;
  } catch (e) {
    container.innerHTML = aiErrorHtml(e);
  }
}

function dietCard(bs) {
  const pick = bs.pick_movie;
  if (!pick) return '';
  const poster = pick.poster_url ? `<img src="${pick.poster_url}" onerror="this.parentElement.innerHTML='🎬'">` : '🎬';
  const catLabel = bs.category === 'genre' ? `Genre gap: ${bs.value}` : bs.category === 'language' ? `Language gap: ${bs.value}` : `Decade gap: ${bs.value}`;
  return `
    <div class="rec-card" onclick="openMovie(${pick.id})">
      <div class="gem-poster">${poster}</div>
      <div class="rec-content">
        <div style="font-size:0.75rem;font-weight:700;color:var(--accent);text-transform:uppercase;margin-bottom:4px">${catLabel}</div>
        <div class="rec-title">${pick.title}</div>
        <div class="rec-genres">${(pick.genres || []).join(' · ')} · ${pick.release_year}</div>
        ${(bs.why_start_here || bs.why) ? `<div class="rec-reason">✦ ${bs.why_start_here || bs.why}</div>` : ''}
        ${pick.average_rating ? `<div class="rec-rating">★ ${pick.average_rating.toFixed(1)} avg</div>` : ''}
      </div>
    </div>`;
}

// ---- ERA ANALYSIS ----
async function doEraAnalysis(decade) {
  document.querySelectorAll('.era-btn').forEach(b => {
    b.classList.toggle('active', b.textContent.trim().startsWith(String(decade)));
  });

  const container = document.getElementById('eraResult');
  container.innerHTML = `<div class="loading"><div class="spinner"></div><p>Analyzing the ${decade}s...</p></div>`;

  try {
    const data = await apiFetch(`/api/ai/insights/era?decade=${decade}`);
    if (data.message) {
      container.innerHTML = `<div class="ai-result-card"><p style="color:var(--text-muted)">${data.message}</p></div>`;
      return;
    }
    container.innerHTML = renderEraCard(data);
  } catch (e) {
    container.innerHTML = aiErrorHtml(e);
  }
}

function renderEraCard(data) {
  const themes   = (data.dominant_themes || []).map(t => `<span class="dna-tag theme">${t}</span>`).join('');
  const defining = data.defining_film ? `<span class="dna-tag">${data.defining_film}</span>` : '';
  const moviesHtml = (data.movies || []).map(m => `
    <div class="film-card" onclick="openMovie(${m.id})">
      <div class="film-title">${m.title}</div>
      <div class="film-year">${m.release_year}</div>
      <div class="film-rating">★ ${m.average_rating ? m.average_rating.toFixed(1) : '—'}</div>
    </div>`).join('');
  const overview = data.narrative || data.overview || '';
  return `
    <div class="ai-result-card">
      <div class="ai-result-header">
        <span class="ai-badge">🕰️ ${data.decade}s Cinema</span>
        <span style="color:var(--text-dim);font-size:0.85rem">${data.movie_count} films in CineDB</span>
      </div>
      ${overview   ? `<p class="ai-summary">${overview}</p>` : ''}
      ${themes     ? `<div class="dna-row"><span class="dna-label">Themes</span><div class="dna-tags">${themes}</div></div>` : ''}
      ${defining   ? `<div class="dna-row"><span class="dna-label">Defining Film</span><div class="dna-tags">${defining}</div></div>` : ''}
      ${data.style_notes ? `<div class="compare-section"><span class="compare-label">Style</span><p class="compare-text">${data.style_notes}</p></div>` : ''}
      ${data.cultural_context ? `<div class="compare-section"><span class="compare-label">Cultural Context</span><p class="compare-text">${data.cultural_context}</p></div>` : ''}
    </div>
    ${moviesHtml ? `<div style="margin-top:24px"><h3 style="font-size:1.1rem;margin-bottom:16px;font-family:'Playfair Display',serif">Films from the ${data.decade}s in CineDB</h3><div class="filmography-grid">${moviesHtml}</div></div>` : ''}`;
}
