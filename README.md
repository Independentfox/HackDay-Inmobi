# CineDB — IMDB-Style Movie Database

> A full-stack movie information platform built for the intern hackathon. FastAPI + PostgreSQL backend, dark-themed SPA frontend, Kubernetes deployment with 2 API replicas, and a floating AI assistant — no paid API keys required.

---

## Quick Start

### Docker Compose (local dev)
```bash
cd imdb-api
make local-up        # starts postgres + api, runs migrations + seed
# UI:       http://localhost:8000/
# API docs: http://localhost:8000/docs
```

### Kubernetes (the deliverable)
```bash
make deploy          # minikube start → docker build → kubectl apply → wait → print URL
make status          # kubectl get all -n imdb
make clean           # tear down namespace + stop minikube
```

### Manual (no Docker)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. DATABASE_URL=postgresql://postgres:postgres@localhost:5432/imdb alembic upgrade head
DATABASE_URL=... python seed.py
DATABASE_URL=... uvicorn app.main:app --port 8000 --reload
```

---

## Features

### Core (spec requirements)
| Feature | Notes |
|---|---|
| Movie CRUD | Full create / partial-update / delete with cascade |
| People & Credits | Actors require `character_name`; one person can hold multiple roles on one film |
| Ratings (1–10, upsert) | Rejects unreleased movies; running average denormalised on `movies` row |
| Reviews (text + rating, upsert) | Helpful-vote endpoint; top 5 by helpful votes on movie detail |
| Bayesian Top Rated | `WR = (v/(v+m))·R + (m/(v+m))·C`, `m=10`, min 10 ratings, top 50 |
| Trending | Most ratings in last N days (default 7), configurable `?days=` param |
| Movie Detail | Cast grouped by role, full 1–10 rating distribution, top reviews |
| Filmography | Grouped by `"As Actor"` / `"As Director"` etc., year-desc |
| Six Degrees of Separation | BFS through person↔movie↔person graph, bounded at depth 6 |
| Search | Filters: title, genre, year range, min rating, certificate (U/UA/A), language |

### Beyond the Spec
| Feature | Notes |
|---|---|
| User Auth | Sign up / sign in with bcrypt-hashed passwords; session stored in `localStorage` |
| User Dashboard | Personal ratings history, reviews, watchlist — at `/user` |
| Watchlist | Per-user; enriched with movie title/year/rating/poster |
| Similar Movies | Genre-overlap recommendations, tiebreaker = average rating |
| People Search | Partial name match |
| Platform Stats | Counts, avg platform score, most-rated, highest-rated |
| **CineBot** | Floating gold chatbot (🎬 FAB) — tree-based questionnaire wired to live API; auto-opens on home page; no LLM required |
| AI Layer | 18 endpoints (mood search, review insights, movie DNA, recommendations, six-degrees narrator, trivia, era analysis, watch-party picker, etc.) — powered by local Ollama; returns `503` cleanly if unavailable |
| Poster Fetcher | `fetch_posters.py` — batch-updates `poster_url` from a remote source |
| Stress Test | Full report in `STRESS_TEST.md` — 5 load + chaos scenarios against live K8s |

---

## Architecture

```
[Browser]
   │
   ├── /                → dark SPA (vanilla JS, no build step)
   ├── /signin          → auth page
   ├── /user            → user dashboard
   ├── /docs            → Swagger UI
   └── /api/*           → FastAPI
                              │
                         [PostgreSQL 16]
                  movies, people, credits, users,
                  ratings, reviews, watchlist_items
```

**Kubernetes layout:**
```
[Client] → NodePort:30080 → [K8s Service]
                                  │
                    ┌─────────────┴─────────────┐
               [API Pod 1]              [API Pod 2]        ← anti-affinity spread
               (FastAPI)                (FastAPI)
                    └─────────────┬─────────────┘
                           [Postgres StatefulSet]
                           (1Gi PVC, persistent)
                                  │
                           [initContainer]
                      alembic upgrade head && python seed.py
```

PodDisruptionBudget ensures at least 1 API replica stays up during voluntary disruptions.

---

## API Reference

All endpoints are at `http://localhost:8000`. Interactive docs at `/docs`.

### Movies
| Method | Path | Description |
|---|---|---|
| `POST` | `/api/movies/` | Create movie |
| `PATCH` | `/api/movies/{id}` | Partial update |
| `DELETE` | `/api/movies/{id}` | Delete (cascades) |
| `GET` | `/api/movies/{id}` | Detail: cast, rating dist, top reviews |
| `GET` | `/api/movies/search` | `title`, `genre`, `year_min`, `year_max`, `min_rating`, `certificate`, `language` |
| `GET` | `/api/movies/top-rated` | Bayesian top 50 |
| `GET` | `/api/movies/trending` | Most rated in `?days=7` window |
| `GET` | `/api/movies/{id}/similar` | Genre-overlap picks |

### People
| Method | Path | Description |
|---|---|---|
| `POST` | `/api/people/` | Create person |
| `GET` | `/api/people/search?name=` | Partial name match |
| `GET` | `/api/people/{id}` | Profile |
| `GET` | `/api/people/{id}/filmography` | Grouped by role, year-desc |
| `GET` | `/api/people/{id}/known-for` | Top 4 by average rating |
| `GET` | `/api/people/six-degrees/{a}/{b}` | Shortest path, returns chain + movie titles |

### Credits / Ratings / Reviews / Users / Watchlist / Stats
| Method | Path | Description |
|---|---|---|
| `POST` | `/api/credits/` | Link person to movie |
| `POST` | `/api/ratings/` | Rate 1–10 (upsert) |
| `POST` | `/api/reviews/` | Write review (upsert) |
| `POST` | `/api/reviews/helpful` | +1 helpful vote |
| `POST` | `/api/users/` | Sign up |
| `POST` | `/api/users/signin` | Sign in (returns user object) |
| `GET` | `/api/users/{id}/ratings` | User's rating history with movie info |
| `GET` | `/api/users/{id}/reviews` | User's review history |
| `POST` | `/api/watchlist/` | Add to watchlist |
| `GET` | `/api/watchlist/{user_id}` | Get watchlist |
| `DELETE` | `/api/watchlist/{user_id}/{movie_id}` | Remove from watchlist |
| `GET` | `/api/stats/` | Platform-wide stats |

### AI (`/api/ai/*`) — requires local Ollama or returns 503
| Path | Description |
|---|---|
| `POST /search` | Natural language → structured filters → results |
| `GET /movies/{id}/insights` | Review synthesis: pros, cons, sentiment |
| `GET /movies/{id}/dna` | Thematic fingerprint |
| `GET /movies/{id}/trivia` | Generated trivia |
| `GET /movies/{id}/vibe` | Mood/vibe analysis |
| `GET /movies/{id}/pitch` | Elevator pitch |
| `GET /movies/compare?a=&b=` | Head-to-head comparison |
| `GET /users/{id}/recommend` | Personalised picks from taste profile |
| `GET /users/{id}/hidden-gems` | Under-the-radar suggestions |
| `GET /users/{id}/blind-spots` | Genre gaps in watch history |
| `GET /users/{id}/watchlist-priority` | Smart watchlist ordering |
| `GET /people/{id}/career-lens` | Career arc analysis |
| `GET /six-degrees/{a}/{b}/story` | Narrative of the BFS chain |
| `GET /insights/era` | Cross-era movie analysis |
| `POST /mood` | Mood → curated picks |
| `POST /watch-party` | Group preference → best film |
| `POST /chat` | Tool-calling chatbot with DB access |
| `DELETE /chat/{session_id}` | Clear session |

### Health
| Path | Description |
|---|---|
| `GET /health` | Liveness — always 200 |
| `GET /ready` | Readiness — runs `SELECT 1`, 503 on DB failure |

---

## Database Schema

7 tables, all foreign keys cascade on delete.

```
users ──────────────────────────────────────────┐
  id, username (UQ), password_hash              │
                                                 │
movies ──────────────────────────────────┐       │
  id, title, release_year, genres[],    │       │
  plot_summary, runtime_min, language,  │       │
  certificate ∈ {U,UA,A},              │       │
  poster_url,                           │       │
  rating_sum*, rating_count*,           │       │
  average_rating* (denormalised)        │       │
                                        │       │
people ──────────────────┐              │       │
  id, name, birth_year,  │              │       │
  bio, photo_url         │              │       │
                         │              │       │
credits ─────────────────┘──────────────┘       │
  person_id, movie_id, role_type,               │
  character_name                                │
  UQ(person, movie, role_type)                  │
                                                │
ratings ────────────────────────────────────────┤
  user_id, movie_id, score 1–10, ts             │
  UQ(user, movie)                               │
                                                │
reviews ────────────────────────────────────────┤
  user_id, movie_id, rating 1–10,               │
  text, helpful_votes, ts                       │
  UQ(user, movie)                               │
                                                │
watchlist_items ────────────────────────────────┘
  user_id, movie_id, added_at
  UQ(user, movie)
```

Key invariants enforced at DB level: `score/rating ∈ [1,10]`, `certificate ∈ {U,UA,A}`, one rating and one review per (user, movie). Rating averages are denormalised — updated transactionally in the rating handler, never recomputed.

---

## Tech Stack

| Layer | Tech |
|---|---|
| API | FastAPI 0.115 + Uvicorn |
| ORM | SQLAlchemy 2.0 + Alembic |
| Database | PostgreSQL 16 |
| Auth | bcrypt (password hashing) |
| AI | Ollama (local LLM — llama3.2:3b / llama3.1:8b) |
| Container | Docker |
| Orchestration | Kubernetes (Minikube) |
| Frontend | Vanilla JS + CSS — zero build step, dark gold theme |

---

## Project Layout

```
imdb-api/
├── app/
│   ├── main.py              FastAPI app, CORS, static mount, health probes
│   ├── database.py          Engine, SessionLocal, get_db
│   ├── models/              SQLAlchemy ORM — Movie, Person, Credit, User, Rating, Review, WatchlistItem
│   ├── schemas/             Pydantic request/response models
│   ├── routers/             One file per resource + ai.py (18 AI endpoints)
│   └── services/
│       ├── bayesian.py      Top-rated formula
│       ├── six_degrees.py   BFS (raw SQL, bounded at depth 6)
│       ├── auth.py          bcrypt hash + verify
│       ├── ai_agent.py      Ollama wrappers (16 functions)
│       └── chatbot.py       Tool-calling chatbot with 9 DB tools
├── alembic/versions/        3 migrations: initial schema, helpful_votes, password_hash
├── k8s/                     Namespace, ConfigMap, Secret, StatefulSet, Deployment (×2), Service, PDB
├── static/
│   ├── index.html           Main SPA
│   ├── signin.html          Auth page
│   ├── user.html            User dashboard
│   ├── js/app.js            ~1900 LOC — routing, pages, CineBot
│   └── js/user.js           ~400 LOC — dashboard logic
├── tests/                   pytest, 108+ tests across all routers
├── seed.py                  20 users, 31 people, ~30 movies, credits, ratings, reviews
├── fetch_posters.py         Batch poster URL updater
├── docker-compose.yml
├── Dockerfile
├── Makefile
└── STRESS_TEST.md           Load + chaos test report (5 scenarios, K8s)
```

---

## CineBot

A floating 🎬 button fixed to the bottom-right corner. Clicking it opens a gold-themed chat panel that guides users through a branching questionnaire — by mood, genre, language, decade, or occasion — and fetches real results from the live API. No LLM dependency; works entirely offline with the DB. Auto-opens once on the home page per session.

---

## Development

```bash
# Run tests
make test

# Apply migrations manually
PYTHONPATH=. DATABASE_URL=postgresql://... alembic upgrade head

# Re-seed
DATABASE_URL=... python seed.py

# Fetch posters
DATABASE_URL=... python fetch_posters.py
```

### Makefile targets
```
make local-up      Start via Docker Compose (migrations + seed included)
make local-down    Stop and remove volumes
make test          Run pytest
make deploy        Full Kubernetes deploy (build → apply → wait → URL)
make status        kubectl get all -n imdb
make clean         Tear down K8s namespace + stop minikube
make health        Quick /health check
```

---

## Demo Script (3 minutes)

1. `make deploy` — one command, comes up with seed data, 2 API replicas
2. Open `/` → dark UI; CineBot auto-opens, try "Find by mood → Make me laugh → Any language"
3. Search "baahubali" → movie detail with cast grouped by role, full 1–10 distribution
4. `/api/movies/top-rated` → Bayesian ranking (note: 12×9.0 doesn't beat 5000×8.7)
5. `/api/people/six-degrees/1/11` → Shah Rukh Khan ↔ S.S. Rajamouli shortest path
6. `kubectl get pods -n imdb` → 2 API replicas + Postgres StatefulSet
7. `kubectl delete pod <api-pod>` → watch it self-heal, PDB keeps other replica up
8. Sign up → rate a movie → view your dashboard at `/user`
