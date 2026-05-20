/* =========================================================
   CineDB — Frontend Application
   ========================================================= */

const API = '';  // same origin
let currentUser = null;
let currentMovieId = null;
let selectedStarRating = 0;

// ---- INIT ----
document.addEventListener('DOMContentLoaded', async () => {
  await loadUsers();
  await loadHomePage();
  await navigateToPath(window.location.pathname, false);
  setupPersonAutocomplete('sixDegA');
  setupPersonAutocomplete('sixDegB');
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

async function loadUsers() {
  try {
    const res = await fetch(`${API}/api/users/?limit=50`);
    const users = await res.json();
    const sel = document.getElementById('userSelect');
    users.forEach(u => {
      const opt = document.createElement('option');
      opt.value = u.id;
      opt.textContent = u.username;
      sel.appendChild(opt);
    });
    if (users.length > 0) {
      sel.value = users[0].id;
      setUser(users[0].id);
    }
  } catch (e) {
    console.error('Failed to load users', e);
  }
}

function setUser(id) {
  currentUser = id ? parseInt(id) : null;
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
    const [detail, similar, watchlist] = await Promise.all([
      apiFetch(`/api/movies/${movieId}`),
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
  const reviewsHtml = m.top_reviews && m.top_reviews.length > 0
    ? m.top_reviews.map(r => `
        <div class="review-card">
          <div class="review-header">
            <span class="review-user">@${r.username}</span>
            <span class="review-rating">★ ${r.rating}/10</span>
          </div>
          <div class="review-text">${r.text}</div>
          <div class="review-helpful">
            <span>👍 ${r.helpful_votes} found helpful</span>
            <button class="helpful-btn" onclick="voteHelpful(${r.id})">Mark Helpful</button>
          </div>
        </div>
      `).join('')
    : '<p style="color: var(--text-muted)">No reviews yet. Be the first!</p>';

  // Similar movies
  const similarHtml = similar && similar.length > 0
    ? similar.slice(0, 6).map(s => movieCard(s)).join('')
    : '<p style="color: var(--text-muted)">No similar movies found.</p>';

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
          <button class="btn btn-ai" onclick="openMovieAiInsights(${m.id})">✦ AI Insights</button>
          <button class="btn btn-ai btn-ai-outline" onclick="openMovieAiDna(${m.id})">🧬 DNA</button>
        </div>
        <div id="movieAiPanel-${m.id}" class="movie-ai-panel hidden"></div>
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

    <div style="margin-top:40px">
      <div class="section-header">
        <h2 style="font-size:1.3rem;font-family:'Playfair Display',serif">Similar Movies</h2>
      </div>
      <div class="movie-grid">${similarHtml}</div>
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
  const genre = document.getElementById('filterGenre').value.trim();
  const yearMin = document.getElementById('filterYearMin').value;
  const yearMax = document.getElementById('filterYearMax').value;
  const minRating = document.getElementById('filterMinRating').value;
  const cert = document.getElementById('filterCert').value;
  const lang = document.getElementById('filterLang').value.trim();

  const params = new URLSearchParams();
  if (title) params.append('title', title);
  if (genre) params.append('genre', genre);
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
  ['filterTitle','filterGenre','filterLang','filterYearMin','filterYearMax','filterMinRating'].forEach(id => {
    document.getElementById(id).value = '';
  });
  document.getElementById('filterCert').value = '';
  document.getElementById('searchResults').innerHTML = '';
  document.getElementById('searchEmpty').classList.add('hidden');
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
function openRatingModal(movieId, movieTitle) {
  if (!currentUser) { showToast('Please select a user first', 'error'); return; }
  currentMovieId = movieId;
  document.getElementById('modalMovieName').textContent = movieTitle;
  document.getElementById('reviewText').value = '';
  selectedStarRating = 0;
  renderStars(0);
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

async function voteHelpful(reviewId) {
  try {
    await apiFetch('/api/reviews/helpful', {
      method: 'POST',
      body: JSON.stringify({ review_id: reviewId })
    });
    showToast('Marked as helpful 👍', 'success');
    if (currentMovieId) openMovie(currentMovieId);
  } catch (e) {
    showToast('Failed', 'error');
  }
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
// AI FEATURES
// =====================================================================

function showAiTab(tab) {
  ['search', 'insights', 'dna', 'recommend'].forEach(t => {
    document.getElementById(`ai-panel-${t}`).classList.toggle('hidden', t !== tab);
    document.getElementById(`ai-panel-${t}`).classList.toggle('active', t === tab);
    document.getElementById(`ai-tab-btn-${t}`).classList.toggle('active', t === tab);
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
    return `<div class="ai-result-card"><p style="color:var(--gold)">⚠️ AI features require <code>ANTHROPIC_API_KEY</code> to be set in the server environment.</p></div>`;
  }
  return `<div class="ai-result-card"><p style="color:var(--text-muted)">AI analysis failed. Please try again.</p></div>`;
}
