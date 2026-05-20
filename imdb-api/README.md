# CineDB — IMDB-Style Movie Database API

> A complete movie information platform with Bayesian ratings, reviews, Six Degrees of Separation, watchlists, and a beautiful dark-themed UI. Built with FastAPI + PostgreSQL, deployable via Docker Compose or Kubernetes.

---

## Quick Start

### Option 1 — Docker Compose (recommended for development)
```bash
cd imdb-api
make local-up
```
- UI: http://localhost:8000/
- API docs: http://localhost:8000/docs

### Option 2 — Kubernetes (Minikube)
```bash
make deploy
```

---

## Architecture

```
[Browser] → http://localhost:8000/
               │
               ├── / → Beautiful dark UI (SPA)
               ├── /docs → Swagger UI
               └── /api/* → FastAPI endpoints
                               │
                          [PostgreSQL 16]
                       (ratings, movies, people, credits, reviews, watchlists)
```

**Kubernetes:**
```
[Client] → [NodePort:30080] → [K8s Service] → [FastAPI Pod ×2] → [PostgreSQL StatefulSet]
                                                    ↑
                                         [ConfigMap + Secret]
                                         [initContainer: migrate + seed]
```

---

## API Endpoints

| # | Method | Path | Description |
|---|--------|------|-------------|
| 1 | POST | `/api/movies/` | Add a movie |
| 2 | PATCH | `/api/movies/{id}` | Update a movie |
| 3 | DELETE | `/api/movies/{id}` | Delete a movie |
| 4 | GET | `/api/movies/{id}` | Movie detail (cast grouped, rating dist, top reviews) |
| 5 | GET | `/api/movies/search` | Search by title, genre, year, rating, certificate, language |
| 6 | GET | `/api/movies/top-rated` | Top 50 by Bayesian weighted average (min 10 ratings) |
| 7 | GET | `/api/movies/trending` | Most rated in the last 7 days |
| 8 | GET | `/api/movies/{id}/similar` | Genre-similarity recommendations |
| 9 | POST | `/api/people/` | Add a person |
| 10 | GET | `/api/people/search` | Search people by name |
| 11 | GET | `/api/people/{id}` | Person detail |
| 12 | GET | `/api/people/{id}/filmography` | Full filmography grouped by role |
| 13 | GET | `/api/people/{id}/known-for` | Top 4 highest-rated movies |
| 14 | GET | `/api/people/six-degrees/{a}/{b}` | Six Degrees of Separation |
| 15 | POST | `/api/credits/` | Link person to movie |
| 16 | POST | `/api/ratings/` | Rate a movie (upsert, 1–10) |
| 17 | POST | `/api/reviews/` | Write a review (upsert) |
| 18 | POST | `/api/reviews/helpful` | Vote a review as helpful |
| 19 | POST | `/api/users/` | Create user |
| 20 | GET | `/api/users/{id}` | Get user |
| 21 | POST | `/api/watchlist/` | Add to watchlist |
| 22 | GET | `/api/watchlist/{user_id}` | Get user's watchlist |
| 23 | DELETE | `/api/watchlist/{user_id}/{movie_id}` | Remove from watchlist |
| 24 | GET | `/api/stats/` | Platform-wide statistics |
| 25 | GET | `/health` | Liveness probe |
| 26 | GET | `/ready` | Readiness probe (DB check) |

---

## Features

### Core (from spec)
- **Full CRUD** for movies, people, credits, users
- **Bayesian Weighted Rating** — `WR = (v/(v+m)) * R + (m/(v+m)) * C` with `m=10`
- **Trending** — movies with most ratings in last 7 days
- **Movie Detail** — cast grouped by role, rating distribution (1–10), top reviews by helpful votes
- **Filmography** — grouped by role (As Actor, As Director, etc.)
- **Six Degrees of Separation** — BFS algorithm through person↔movie↔person graph
- **Search** — title, genre, year range, min rating, certificate, language

### Additional Features
- **Watchlist** — per-user movie watchlists
- **Similar Movies** — genre-overlap recommendations
- **People Search** — search people by name
- **Platform Stats** — total movies, users, ratings, avg platform score
- **Beautiful Dark UI** — fully interactive SPA with movie cards, filmography, Six Degrees visualizer
- **CORS enabled** — works with any frontend
- **Health + Readiness probes** — K8s-ready

---

## Tech Stack

| Layer | Tech |
|-------|------|
| API | FastAPI 0.115 |
| ORM | SQLAlchemy 2.0 |
| DB | PostgreSQL 16 |
| Migrations | Alembic |
| Container | Docker |
| Orchestration | Kubernetes (Minikube) |
| Frontend | Vanilla JS + CSS (dark theme, no build step) |

---

## Development

### Run migrations manually
```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/imdb alembic upgrade head
```

### Seed sample data
```bash
make seed
# or directly:
DATABASE_URL=... python seed.py
```

### Run tests
```bash
make test
```

### Useful make targets
```bash
make local-up      # Start with Docker Compose
make local-down    # Stop and remove volumes
make test          # Run test suite
make deploy        # Deploy to Minikube
make clean         # Tear down K8s namespace
make status        # Check K8s pod status
make health        # Quick health check
```

---

## Six Degrees Demo

Visit `/api/people/six-degrees/1/11` to see the connection between Shah Rukh Khan and S.S. Rajamouli:

```
Shah Rukh Khan
  └─ via 3 Idiots → Aamir Khan
       └─ via Dangal → ...
```

Or use the **UI** — go to a person's profile, click "Six Degrees", and find connections visually.

---

## Winning Demo Script

1. `make deploy` — one-command deployment
2. Open `/` — show the beautiful dark UI
3. `/api/movies/search?title=baahubali` — search
4. `/api/movies/top-rated` — Bayesian rankings
5. `/api/movies/trending` — time-based trending
6. `/api/movies/{id}` — full movie detail with cast, rating distribution, reviews
7. `/api/people/{id}/filmography` — filmography grouped by role
8. **`/api/people/six-degrees/1/11`** — the showstopper Six Degrees result
9. `kubectl get pods -n imdb` — 2 API replicas + 1 DB
10. Kill a pod → watch it self-heal
