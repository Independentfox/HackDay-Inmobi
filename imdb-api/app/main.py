from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import os

from app.routers import movies, people, credits, users, ratings, reviews, watchlist, stats, ai


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="CineDB — IMDB-Style Movie Database API",
    description=(
        "A comprehensive movie information platform featuring ratings, reviews, search, "
        "Bayesian top-rated rankings, trending detection, Six Degrees of Separation, "
        "watchlists, and platform statistics."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files for the UI
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}


@app.get("/ready", tags=["Health"])
def ready():
    from app.database import engine
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        from fastapi import Response
        return Response(
            content='{"status": "not ready"}',
            status_code=503,
            media_type="application/json"
        )


app.include_router(users.router)
app.include_router(movies.router)
app.include_router(people.router)
app.include_router(credits.router)
app.include_router(ratings.router)
app.include_router(reviews.router)
app.include_router(watchlist.router)
app.include_router(stats.router)
app.include_router(ai.router)


@app.get("/{full_path:path}", include_in_schema=False)
def serve_spa(full_path: str):
    ui_path = os.path.join(os.path.dirname(__file__), "..", "static", "index.html")
    if os.path.isfile(ui_path):
        return FileResponse(ui_path)
    return {"message": "CineDB API is running. Visit /docs for API documentation."}
