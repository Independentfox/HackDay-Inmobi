const API = '';
let currentUser = null;
let currentMovieId = null;
let selectedStarRating = 0;

window.addEventListener('DOMContentLoaded', () => {
  initSession();
  if (currentUser) loadDashboard();
});

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

async function loadDashboard() {
  const summary = document.getElementById('dashboardSummary');
  const ratingsContainer = document.getElementById('dashboardRatings');
  const reviewsContainer = document.getElementById('dashboardReviews');
  const watchlistContainer = document.getElementById('dashboardWatchlist');
  const ratingsEmpty = document.getElementById('dashboardRatingsEmpty');
  const reviewsEmpty = document.getElementById('dashboardReviewsEmpty');
  const watchlistEmpty = document.getElementById('dashboardWatchlistEmpty');

  if (!currentUser) {
    summary.innerHTML = '<div class="empty-state"><div class="empty-icon">👤</div><p>Select a user to load your dashboard.</p></div>';
    ratingsContainer.innerHTML = '';
    reviewsContainer.innerHTML = '';
    watchlistContainer.innerHTML = '';
    ratingsEmpty.classList.remove('hidden');
    reviewsEmpty.classList.remove('hidden');
    watchlistEmpty.classList.remove('hidden');
    return;
  }

  summary.innerHTML = '<div class="loading"><div class="spinner"></div><p>Loading dashboard...</p></div>';
  ratingsContainer.innerHTML = '';
  reviewsContainer.innerHTML = '';
  watchlistContainer.innerHTML = '';
  ratingsEmpty.classList.add('hidden');
  reviewsEmpty.classList.add('hidden');
  watchlistEmpty.classList.add('hidden');

  try {
    const [ratings, reviews, watchlist] = await Promise.all([
      apiFetch(`/api/users/${currentUser}/ratings`),
      apiFetch(`/api/users/${currentUser}/reviews`),
      apiFetch(`/api/watchlist/${currentUser}`)
    ]);

    renderDashboardSummary(ratings.length, reviews.length, watchlist.length);
    renderDashboardRatings(ratings);
    renderDashboardReviews(reviews);
    renderDashboardWatchlist(watchlist);
  } catch (err) {
    summary.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div><p>Could not load dashboard data.</p></div>';
    ratingsContainer.innerHTML = '';
    reviewsContainer.innerHTML = '';
    watchlistContainer.innerHTML = '';
  }
}

function renderDashboardSummary(ratingCount, reviewCount, watchlistCount) {
  document.getElementById('dashboardSummary').innerHTML = `
    <div class="stat-card"><div class="stat-icon">⭐</div><div class="stat-num">${ratingCount}</div><div class="stat-label">My Ratings</div></div>
    <div class="stat-card"><div class="stat-icon">📝</div><div class="stat-num">${reviewCount}</div><div class="stat-label">My Reviews</div></div>
    <div class="stat-card"><div class="stat-icon">📺</div><div class="stat-num">${watchlistCount}</div><div class="stat-label">Watchlist Items</div></div>
  `;
}

function renderDashboardRatings(ratings) {
  const container = document.getElementById('dashboardRatings');
  const empty = document.getElementById('dashboardRatingsEmpty');
  if (!ratings || !ratings.length) {
    container.innerHTML = '';
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');
  container.innerHTML = ratings.map(r => `
    <div class="dashboard-card">
      <div class="dashboard-card-header">
        <div>
          <div class="dashboard-card-title">${r.movie_title}</div>
          <div class="dashboard-card-subtitle">${r.movie_year} · ★ ${r.score}/10 · Avg ${r.movie_average_rating.toFixed(1)}</div>
        </div>
      </div>
      <div class="dashboard-card-actions">
        <button class="btn btn-ghost btn-sm" onclick='openEditModal(${r.movie_id}, ${JSON.stringify(r.movie_title)}, ${r.score}, ${JSON.stringify(r.review_text || '')})'>Edit</button>
      </div>
    </div>
  `).join('');
}

function renderDashboardReviews(reviews) {
  const container = document.getElementById('dashboardReviews');
  const empty = document.getElementById('dashboardReviewsEmpty');
  if (!reviews || !reviews.length) {
    container.innerHTML = '';
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');
  container.innerHTML = reviews.map(r => `
    <div class="review-card dashboard-review-card">
      <div class="review-header">
        <span class="review-user">${r.movie_title}</span>
        <span class="review-rating">★ ${r.rating}/10</span>
      </div>
      <div class="review-text">${r.text}</div>
      <div class="dashboard-card-meta">${r.movie_year} · Avg ${r.movie_average_rating.toFixed(1)}</div>
      <div class="review-helpful dashboard-review-actions">
        <button class="btn btn-ghost btn-sm" onclick='openEditModal(${r.movie_id}, ${JSON.stringify(r.movie_title)}, ${r.rating}, ${JSON.stringify(r.text)})'>Edit</button>
      </div>
    </div>
  `).join('');
}

function renderDashboardWatchlist(items) {
  const container = document.getElementById('dashboardWatchlist');
  const empty = document.getElementById('dashboardWatchlistEmpty');
  if (!items || !items.length) {
    container.innerHTML = '';
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');
  container.innerHTML = items.map(item => `
    <div class="dashboard-card dashboard-watchlist-card">
      <div class="dashboard-card-header">
        <div>
          <div class="dashboard-card-title">${item.movie_title}</div>
          <div class="dashboard-card-subtitle">${item.movie_year} · ★ ${item.movie_rating.toFixed(1)}</div>
        </div>
      </div>
      <div class="dashboard-card-actions">
        <button class="btn btn-ghost btn-sm" onclick="removeWatchlistItem(${item.movie_id})">Remove</button>
      </div>
    </div>
  `).join('');
}

function openEditModal(movieId, movieTitle, currentScore = 0, currentText = '') {
  if (!currentUser) {
    showToast('Select a user first', 'error');
    return;
  }
  currentMovieId = movieId;
  selectedStarRating = currentScore || 0;
  document.getElementById('modalTitle').textContent = `Edit ${movieTitle}`;
  document.getElementById('modalSubtitle').textContent = movieTitle;
  document.getElementById('dashboardReviewText').value = currentText;
  document.getElementById('dashboardSelectedRating').textContent = selectedStarRating ? `${selectedStarRating}/10 — ${ratingLabel(selectedStarRating)}` : 'Tap a star to rate';
  renderStars(selectedStarRating);
  document.getElementById('dashboardModal').classList.remove('hidden');
}

function closeModal() {
  document.getElementById('dashboardModal').classList.add('hidden');
}

function renderStars(selected) {
  const container = document.getElementById('dashboardStars');
  container.innerHTML = '';
  for (let i = 1; i <= 10; i += 1) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `star-btn ${i <= selected ? 'active' : ''}`;
    button.textContent = '★';
    button.onclick = () => {
      selectedStarRating = i;
      document.getElementById('dashboardSelectedRating').textContent = `${i}/10 — ${ratingLabel(i)}`;
      renderStars(i);
    };
    container.appendChild(button);
  }
}

function ratingLabel(value) {
  if (value >= 9) return 'Masterpiece';
  if (value >= 8) return 'Excellent';
  if (value >= 7) return 'Great';
  if (value >= 6) return 'Good';
  if (value >= 5) return 'Average';
  return 'Needs improvement';
}

async function submitDashboardRating() {
  if (!currentMovieId) return;
  if (!selectedStarRating) {
    showToast('Please choose a rating', 'error');
    return;
  }
  const reviewText = document.getElementById('dashboardReviewText').value.trim();

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
    showToast('Saved!', 'success');
    loadDashboard();
  } catch (err) {
    showToast('Could not save rating/review', 'error');
  }
}

async function removeWatchlistItem(movieId) {
  if (!currentUser) {
    showToast('Select a user first', 'error');
    return;
  }
  try {
    await apiFetch(`/api/watchlist/${currentUser}/${movieId}`, { method: 'DELETE' });
    showToast('Removed from watchlist', 'success');
    loadDashboard();
  } catch (err) {
    showToast('Could not remove watchlist item', 'error');
  }
}

async function apiFetch(url, options = {}) {
  const defaults = {
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' }
  };
  const response = await fetch(`${API}${url}`, { ...defaults, ...options });
  if (!response.ok) {
    const error = new Error('API request failed');
    error.status = response.status;
    throw error;
  }
  if (response.status === 204) return null;
  return response.json();
}

function showToast(message, type = '') {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.className = `toast ${type}`;
  setTimeout(() => toast.classList.add('hidden'), 3000);
}

async function addMovieToWatchlist() {
    if (!currentUser) {
        showToast('Select a user first', 'error');
        return;
    }
    const movieIdInput = document.getElementById('addWatchlistMovieId');
    const movieId = parseInt(movieIdInput.value);

    if (isNaN(movieId) || movieId <= 0) {
        showToast('Please enter a valid Movie ID.', 'error');
        return;
    }

    try {
        await apiFetch(`/api/watchlist/`, {
            method: 'POST',
            body: JSON.stringify({ user_id: currentUser, movie_id: movieId }),
        });
        showToast('Movie added to watchlist successfully!', 'success');
        movieIdInput.value = ''; // Clear input
        loadDashboard(); // Refresh the dashboard
    } catch (error) {
        if (error.status === 409) {
            showToast('Movie is already in your watchlist!', 'warning');
        } else {
            console.error('Error adding movie to watchlist:', error);
            showToast('An error occurred while adding movie to watchlist.', 'error');
        }
    }
}

function openAddMovieModal() {
    document.getElementById('addMovieModal').classList.remove('hidden');
    // Clear form fields
    document.getElementById('newMovieTitle').value = '';
    document.getElementById('newMovieYear').value = '';
    document.getElementById('newMovieGenres').value = '';
    document.getElementById('newMoviePlot').value = '';
    document.getElementById('newMovieRuntime').value = '';
    document.getElementById('newMovieLanguage').value = 'English';
    document.getElementById('newMovieCertificate').value = 'U';
    document.getElementById('newMoviePoster').value = '';
}

function closeAddMovieModal() {
    document.getElementById('addMovieModal').classList.add('hidden');
}

async function submitNewMovie() {
    const title = document.getElementById('newMovieTitle').value.trim();
    const release_year_raw = document.getElementById('newMovieYear').value;
    const release_year = parseInt(release_year_raw, 10);
    const genres = document.getElementById('newMovieGenres').value.split(',').map(g => g.trim()).filter(g => g.length > 0);
    const plot_summary = document.getElementById('newMoviePlot').value.trim();
    const runtime_raw = document.getElementById('newMovieRuntime').value;
    const runtime_minutes = parseInt(runtime_raw, 10);
    const language = document.getElementById('newMovieLanguage').value.trim();
    const certificate = document.getElementById('newMovieCertificate').value;
    const poster_url = document.getElementById('newMoviePoster').value.trim();

    if (!title || release_year_raw === '' || Number.isNaN(release_year) || !genres.length || !plot_summary || runtime_raw === '' || Number.isNaN(runtime_minutes) || !language || !certificate) {
        showToast('Please fill in all required fields (Title, Year, Genres, Plot, Runtime, Language, Certificate).', 'error');
        return;
    }
    if (release_year < 0) {
        showToast('Release year cannot be negative.', 'error');
        return;
    }
    if (runtime_minutes < 0) {
        showToast('Runtime cannot be negative.', 'error');
        return;
    }

    try {
        const response = await apiFetch('/api/movies/', {
            method: 'POST',
            body: JSON.stringify({
                title,
                release_year,
                genres,
                plot_summary,
                runtime_minutes,
                language,
                certificate,
                poster_url: poster_url || null // Allow null for optional poster
            }),
        });
        showToast(`Movie "${response.title}" added successfully!`, 'success');
        closeAddMovieModal();
        // Optionally refresh a movie list if one is displayed
    } catch (error) {
        console.error('Error adding new movie:', error);
        showToast(`Failed to add movie: ${error.detail || error.message || 'Unknown error'}`, 'error');
    }
}
