# CineDB — Repo Overview for the Team

A FastAPI + PostgreSQL backend that implements **Problem 2: IMDB-Style Movie Database** from the intern hackathon, plus a small dark-themed SPA and an optional Claude-powered AI layer. Deployable via `docker compose` for dev or Minikube/K8s for the spec deliverable.

---

## 1. What the spec asks for vs. what we have

| Spec requirement | Where it lives | Status |
|---|---|---|
| Add movie (title, year, genres, plot, runtime, language, certificate U/UA/A) | `POST /api/movies/` → `app/routers/movies.py:18` | ✅ certificate enforced both in Pydantic (`pattern="^(U\|UA\|A)$"`) and DB `CheckConstraint` |
| Add person (name, birth year, bio, photo URL) | `POST /api/people/` → `app/routers/people.py:17` | ✅ |
| Add credit (role + character name for actors) | `POST /api/credits/` → `app/routers/credits.py:12` | ✅ rejects actor credit missing `character_name` |
| Rate movie (1–10, one per user per movie, updates allowed) | `POST /api/ratings/` → `app/routers/ratings.py:12` | ✅ upsert pattern; unique constraint `uq_user_movie_rating` |
| Reject ratings for unreleased movies | `app/routers/ratings.py:22` | ✅ `release_year > current_year` → 400 |
| Write review (text + rating, one per user per movie) | `POST /api/reviews/` → `app/routers/reviews.py:12` | ✅ upsert; unique constraint `uq_user_movie_review` |
| Maintain running average rating | `app/routers/ratings.py:35-45` | ✅ denormalized `rating_sum` / `rating_count` / `average_rating` on `movies` row |
| Movie detail (cast grouped by role, rating distribution 1–10, top 5 reviews by helpful) | `GET /api/movies/{id}` → `app/routers/movies.py:147` | ✅ |
| Person filmography (grouped by role, sorted by year) | `GET /api/people/{id}/filmography` → `app/routers/people.py:53` | ✅ |
| Search (title partial, genre, year range, min rating, certificate) | `GET /api/movies/search` → `app/routers/movies.py:48` | ✅ also adds `language` filter |
| Top Rated (Bayesian, ≥10 ratings, top 50) | `GET /api/movies/top-rated` → `app/routers/movies.py:79`, `app/services/bayesian.py` | ✅ `WR = (v/(v+m))·R + (m/(v+m))·C`, `m=10` |
| Trending (most ratings, last 7 days) | `GET /api/movies/trending` → `app/routers/movies.py:106` | ✅ configurable `days` param |
| Known For (top 4 highest-rated for a person) | `GET /api/people/{id}/known-for` → `app/routers/people.py:85` | ✅ |
| Six Degrees | `GET /api/people/six-degrees/{a}/{b}` → `app/services/six_degrees.py` | ✅ BFS through `credits`, max depth 6 |

**Infra checklist (from spec):**

| Required | We have |
|---|---|
| FastAPI / Spring Boot | FastAPI 0.115 (`requirements.txt`) |
| PostgreSQL | Postgres 16 |
| Dockerize API + DB separately | `Dockerfile` + `docker-compose.yml` |
| K8s Deployment, 2+ replicas | `k8s/api-deployment.yaml` (replicas: 2) |
| StatefulSet for Postgres + PVC | `k8s/postgres-statefulset.yaml` (1Gi PVC) |
| Service (ClusterIP) for DB + NodePort/Ingress for API | DB: headless `postgres-service`; API: NodePort 30080 |
| ConfigMap for DB host/port/pool | `k8s/configmap.yaml` |
| Secret for DB creds | `k8s/secret.yaml` (also holds optional `ANTHROPIC_API_KEY`) |
| Liveness + readiness probes | `/health` and `/ready` wired in deployment |
| Makefile: minikube start → docker build → kubectl apply → migrations → reachable | `make deploy` does exactly this; `initContainer` runs `alembic upgrade head && python seed.py` |

**Extras beyond spec:** watchlists, similar movies (genre overlap), people search, helpful-vote endpoint, platform stats, a dark UI SPA, and 5 optional Claude AI endpoints (NL search, review insights, movie DNA, recommendations, six-degrees narrator).

---

## 2. Database schema

7 tables. All foreign keys cascade on delete.

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   users      │         │   movies     │         │   people     │
│──────────────│         │──────────────│         │──────────────│
│ id PK        │         │ id PK        │         │ id PK        │
│ username UQ  │         │ title (idx)  │         │ name (idx)   │
└──────┬───────┘         │ release_year │         │ birth_year   │
       │                 │ genres[]     │         │ bio          │
       │                 │ plot_summary │         │ photo_url    │
       │                 │ runtime_min  │         └──────┬───────┘
       │                 │ language     │                │
       │                 │ certificate  │                │
       │                 │   ∈ {U,UA,A} │                │
       │                 │ poster_url   │                │
       │                 │ rating_sum*  │                │
       │                 │ rating_count*│                │
       │                 │ average_rating* (denormalised)│
       │                 └──────┬───────┘                │
       │                        │                        │
       │            ┌───────────┼────────────┐           │
       │            │           │            │           │
       ▼            ▼           ▼            ▼           ▼
┌──────────┐  ┌──────────┐ ┌──────────┐ ┌──────────────────┐
│ ratings  │  │ reviews  │ │watchlist │ │     credits      │
│──────────│  │──────────│ │──────────│ │──────────────────│
│ user_id  │  │ user_id  │ │ user_id  │ │ person_id  ──────┘
│ movie_id │  │ movie_id │ │ movie_id │ │ movie_id   ──────┐
│ score    │  │ rating   │ │ added_at │ │ role_type        │
│   1..10  │  │   1..10  │ └──────────┘ │ character_name   │
│ ts       │  │ text     │              │                  │
└──────────┘  │ helpful  │              │ UQ(person,movie, │
              │ ts       │              │     role_type)   │
              │ UQ(u,m)  │              └──────────────────┘
              └──────────┘
```

Migration lives at `alembic/versions/2e6e87d1cc7d_initial_schema.py` — one initial revision, runs automatically in the K8s `initContainer` and in `docker compose` via `alembic upgrade head`.

**Key invariants encoded in the schema:**
- `ratings.score` and `reviews.rating` constrained to `1..10` (DB-level `CHECK`)
- One rating per `(user, movie)` and one review per `(user, movie)` (unique constraints)
- `movies.certificate ∈ {U, UA, A}` (DB-level `CHECK`)
- `credits` unique on `(person, movie, role_type)` so the same person can have multiple roles on one film (e.g. Aamir Khan as actor + producer) but not duplicated
- `movies.rating_sum / rating_count / average_rating` are denormalised — written transactionally in the rating handler so we never recompute averages across the whole `ratings` table

---

## 3. Endpoints — complete list

All under `http://localhost:8000`. Auto-generated Swagger at `/docs`.

### Movies (`app/routers/movies.py`)
| Method | Path | Notes |
|---|---|---|
| `POST`   | `/api/movies/` | create |
| `PATCH`  | `/api/movies/{id}` | partial update |
| `DELETE` | `/api/movies/{id}` | cascades to credits/ratings/reviews/watchlist |
| `GET`    | `/api/movies/search` | filters: `title`, `genre`, `year_min`, `year_max`, `min_rating`, `certificate`, `language`, `skip`, `limit` |
| `GET`    | `/api/movies/top-rated` | Bayesian, `m=10`, returns `bayesian_rating` next to raw `average_rating` |
| `GET`    | `/api/movies/trending` | `?days=7` default, ranks by rating count in window |
| `GET`    | `/api/movies/{id}/similar` | shared-genre overlap, tiebreaker = `average_rating` |
| `GET`    | `/api/movies/{id}` | detail: cast grouped by role, rating dist (1–10), top 5 reviews by `helpful_votes` |

### People (`app/routers/people.py`)
| Method | Path | Notes |
|---|---|---|
| `POST` | `/api/people/` | create |
| `GET`  | `/api/people/search?name=` | partial match |
| `GET`  | `/api/people/{id}` | basic info |
| `GET`  | `/api/people/{id}/filmography` | grouped by `"As Actor"` / `"As Director"` etc., year-desc |
| `GET`  | `/api/people/{id}/known-for` | top 4 by `average_rating` |
| `GET`  | `/api/people/six-degrees/{a}/{b}` | BFS, returns path + movie titles |

### Credits / Ratings / Reviews / Users / Watchlist / Stats
| Method | Path | Notes |
|---|---|---|
| `POST`   | `/api/credits/` | enforces `character_name` for `role_type == "actor"` |
| `GET`    | `/api/credits/movie/{id}` | |
| `DELETE` | `/api/credits/{id}` | |
| `POST`   | `/api/ratings/` | **upsert** — second POST from same user updates score and recomputes movie avg |
| `GET`    | `/api/ratings/movie/{id}` | |
| `POST`   | `/api/reviews/` | upsert (text + rating) |
| `POST`   | `/api/reviews/helpful` | `+1` helpful_votes |
| `GET`    | `/api/reviews/movie/{id}` | paginated |
| `POST`   | `/api/users/` | unique username |
| `GET`    | `/api/users/{id}` | |
| `GET`    | `/api/users/` | list |
| `POST`   | `/api/watchlist/` | unique `(user, movie)` |
| `GET`    | `/api/watchlist/{user_id}` | enriches each row with movie title/year/rating/poster |
| `DELETE` | `/api/watchlist/{user_id}/{movie_id}` | |
| `GET`    | `/api/stats/` | counts + platform avg + most-rated + highest-rated |

### Health & UI
| Method | Path | Notes |
|---|---|---|
| `GET` | `/health` | liveness — static 200 |
| `GET` | `/ready` | readiness — runs `SELECT 1`, 503 on DB failure |
| `GET` | `/` | serves the SPA from `static/index.html` |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc |

### Optional AI layer (`app/routers/ai.py`) — needs `ANTHROPIC_API_KEY`
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/ai/search` | NL query → structured filters → results |
| `GET`  | `/api/ai/movies/{id}/insights` | synthesises reviews into pros/cons/sentiment |
| `GET`  | `/api/ai/movies/{id}/dna` | thematic fingerprint of a movie |
| `GET`  | `/api/ai/users/{id}/recommend` | taste profile + 5 picks |
| `GET`  | `/api/ai/six-degrees/{a}/{b}/story` | narrates the BFS chain |

Returns `503` cleanly if the key isn't set — the rest of the API still works.

---

## 4. Project layout (cheat sheet)

```
imdb-api/
├── app/
│   ├── main.py                ← FastAPI app + CORS + static mount + /health, /ready
│   ├── database.py            ← engine, SessionLocal, get_db dep, Base
│   ├── config.py              ← settings (mostly env-driven)
│   ├── models/                ← SQLAlchemy ORM (Movie, Person, Credit, User, Rating, Review, WatchlistItem)
│   ├── schemas/               ← Pydantic request/response models
│   ├── routers/               ← one file per resource (movies, people, credits, ratings, reviews, users, watchlist, stats, ai)
│   └── services/
│       ├── bayesian.py        ← top-rated formula
│       ├── six_degrees.py     ← BFS (raw SQL via text()) — bounded at depth 6
│       └── ai_agent.py        ← Claude wrappers
├── alembic/                   ← single revision = full initial schema
├── k8s/                       ← namespace, configmap, secret, db statefulset, api deployment, api service
├── static/                    ← dark-themed SPA (vanilla JS, no build step) — 927 LOC of app.js
├── tests/                     ← pytest, ~750 LOC across credits/movies/people/ratings/reviews/users/watchlist/health
├── seed.py                    ← preloads users + ~30 people + ~30 movies + credits + ratings + reviews; runs once via initContainer
├── docker-compose.yml         ← postgres + api, api waits for DB healthcheck
├── Dockerfile                 ← python:3.11-slim, installs psycopg2 build deps
├── Makefile                   ← local-up, local-down, deploy, clean, test, seed, health, status
├── requirements.txt
└── README.md
```

---

## 5. How everything starts up

**Local dev (preferred for hacking):**
```
make local-up      # docker compose up; runs migrations + seeds; serves on :8000
make logs          # tail api logs
make test          # runs pytest against postgres on localhost:5432/imdb_test
make local-down    # stops and wipes volume
```

**Kubernetes (the deliverable):**
```
make deploy
# does: minikube start → eval $(minikube docker-env) → docker build imdb-api:latest
#       → kubectl apply (namespace, secret, configmap, postgres-statefulset)
#       → wait for postgres-0 ready
#       → kubectl apply (api-deployment, api-service)
#       → wait for 2 api pods ready
#       → prints minikube service URL

make status        # kubectl get all -n imdb + URL
make clean         # tears down the namespace and stops minikube
```

The API pod has an `initContainer` that runs `alembic upgrade head && python seed.py` before the app container starts — so a fresh deploy comes up fully populated.

---

## 6. Things worth knowing if you're going to extend it

- **Rating averages are denormalised** on `movies` and updated inside the rating endpoint. If you ever add a way to *delete* a rating, remember to back out `rating_sum` and `rating_count` there too.
- **Six Degrees uses raw SQL** (`text(...)`) instead of ORM joins for speed inside the BFS loop. It's bounded at `MAX_DEGREES = 6` and visits each person at most once.
- **Bayesian top-rated** recomputes the global mean `C` on every request via `func.avg(...)` — fine for hackathon scale, would want caching for real traffic.
- **`character_name` is required iff `role_type == "actor"`** — enforced in the credits router, not the DB.
- **Trending window is configurable** (`?days=N`, default 7) — uses `created_at` on ratings.
- **CORS is wide open** (`allow_origins=["*"]`) — fine for the demo, lock down before anything real.
- **AI endpoints are entirely optional.** Without `ANTHROPIC_API_KEY`, they return a clean 503 and the core API is unaffected. Model in use: `claude-haiku-4-5-20251001`.
- **Tests** cover all routers (`tests/test_*.py`) — about 750 lines total. Run with `make test` against a separate `imdb_test` DB.
- **Two API replicas** in K8s share the same denormalised counters — the rating-update path could race under heavy load. Not an issue for the demo but flag it if anyone asks in the readout.

---

## 7. Demo path for the judges (3 minutes)

1. `make deploy` → one command, comes up with seed data
2. Open `/` → dark UI, search "baahubali"
3. `/api/movies/top-rated` → Bayesian ranking (point out that 12×9.0 doesn't beat 5000×8.7)
4. `/api/movies/trending` → 7-day window
5. `/api/movies/{id}` → cast grouped by role, full 1-10 distribution, top reviews
6. `/api/people/{id}/filmography` → "As Actor", "As Director" buckets
7. **`/api/people/six-degrees/1/11`** → Shah Rukh Khan ↔ S.S. Rajamouli through shared films
8. `kubectl get pods -n imdb` → 2 API replicas + Postgres StatefulSet, both healthy
9. `kubectl delete pod <one-api-pod>` → watch it self-heal
10. (Bonus) `/api/ai/movies/{id}/insights` if the Anthropic key is set — review synthesis on top of the core API
