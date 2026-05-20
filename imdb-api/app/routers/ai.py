"""
AI-powered endpoints for CineDB.

POST /api/ai/search              — Natural language movie search
GET  /api/ai/movies/{id}/insights — Review synthesis + sentiment
GET  /api/ai/movies/{id}/dna      — Movie DNA fingerprint
GET  /api/ai/users/{id}/recommend — Personalized recommendations
GET  /api/ai/six-degrees/{a}/{b}/story — Six Degrees narrative
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional

from app.database import get_db
from app.models import Movie, Person, Credit, Rating, Review, User
from app.services import ai_agent
from app.services.six_degrees import find_connection

router = APIRouter(prefix="/api/ai", tags=["AI"])


def _ai_error(exc: Exception):
    msg = str(exc)
    if "ANTHROPIC_API_KEY" in msg:
        raise HTTPException(
            status_code=503,
            detail="AI features require ANTHROPIC_API_KEY to be set in the environment."
        )
    raise HTTPException(status_code=500, detail=f"AI service error: {msg}")


# ---------------------------------------------------------------------------
# 1. Natural Language Search
# ---------------------------------------------------------------------------

@router.post("/search")
def nl_search(body: dict, db: Session = Depends(get_db)):
    """Convert a natural-language query into structured search results."""
    query = body.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query field is required")

    try:
        parsed = ai_agent.parse_nl_search(query)
    except Exception as e:
        _ai_error(e)

    filters = parsed.get("filters", {})

    q = db.query(Movie)
    if filters.get("title"):
        q = q.filter(Movie.title.ilike(f"%{filters['title']}%"))
    if filters.get("genre"):
        q = q.filter(Movie.genres.any(filters["genre"]))
    if filters.get("language"):
        q = q.filter(Movie.language.ilike(f"%{filters['language']}%"))
    if filters.get("year_min"):
        q = q.filter(Movie.release_year >= int(filters["year_min"]))
    if filters.get("year_max"):
        q = q.filter(Movie.release_year <= int(filters["year_max"]))
    if filters.get("min_rating"):
        q = q.filter(Movie.average_rating >= float(filters["min_rating"]))
    if filters.get("certificate"):
        q = q.filter(Movie.certificate == filters["certificate"])

    movies = q.order_by(desc(Movie.average_rating)).limit(10).all()

    results = [
        {
            "id": m.id,
            "title": m.title,
            "release_year": m.release_year,
            "genres": m.genres,
            "language": m.language,
            "average_rating": m.average_rating,
            "rating_count": m.rating_count,
            "plot_summary": m.plot_summary,
            "poster_url": m.poster_url,
        }
        for m in movies
    ]

    return {
        "query": query,
        "interpretation": parsed.get("interpretation"),
        "filters_applied": filters,
        "results": results,
        "result_count": len(results),
    }


# ---------------------------------------------------------------------------
# 2. Review Insights
# ---------------------------------------------------------------------------

@router.get("/movies/{movie_id}/insights")
def review_insights(movie_id: int, db: Session = Depends(get_db)):
    """Synthesize all reviews for a movie into pros, cons, and consensus."""
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    rows = (
        db.query(Review, User.username)
        .join(User, Review.user_id == User.id)
        .filter(Review.movie_id == movie_id)
        .order_by(desc(Review.helpful_votes))
        .limit(20)
        .all()
    )
    reviews = [
        {
            "username": username,
            "rating": r.rating,
            "text": r.text,
            "helpful_votes": r.helpful_votes
        }
        for r, username in rows
    ]

    try:
        insights = ai_agent.synthesize_review_insights(movie.title, reviews)
    except Exception as e:
        _ai_error(e)

    return {
        "movie_id": movie_id,
        "movie_title": movie.title,
        "review_count": len(reviews),
        **insights,
    }


# ---------------------------------------------------------------------------
# 3. Movie DNA
# ---------------------------------------------------------------------------

@router.get("/movies/{movie_id}/dna")
def movie_dna(movie_id: int, db: Session = Depends(get_db)):
    """Generate a thematic fingerprint — what makes this film unique."""
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    credits = db.query(Credit).filter(Credit.movie_id == movie_id).all()
    cast_crew = []
    for c in credits:
        person = db.query(Person).filter(Person.id == c.person_id).first()
        if person:
            cast_crew.append({
                "name": person.name,
                "role_type": c.role_type,
                "character_name": c.character_name
            })

    # Get similar movie titles for context
    if movie.genres:
        similar = db.query(Movie).filter(
            Movie.id != movie_id,
            Movie.genres.overlap(movie.genres)
        ).order_by(desc(Movie.average_rating)).limit(5).all()
        similar_titles = [m.title for m in similar]
    else:
        similar_titles = []

    movie_dict = {
        "title": movie.title,
        "year": movie.release_year,
        "genres": movie.genres or [],
        "language": movie.language,
        "plot_summary": movie.plot_summary,
        "runtime": movie.runtime_minutes,
        "certificate": movie.certificate,
    }

    try:
        dna = ai_agent.analyze_movie_dna(movie_dict, cast_crew, similar_titles)
    except Exception as e:
        _ai_error(e)

    return {
        "movie_id": movie_id,
        "movie_title": movie.title,
        **dna,
    }


# ---------------------------------------------------------------------------
# 4. Personalized Recommendations
# ---------------------------------------------------------------------------

@router.get("/users/{user_id}/recommend")
def personalized_recommendations(user_id: int, db: Session = Depends(get_db)):
    """Analyze a user's rating history and recommend movies they'll love."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    rated_rows = (
        db.query(Rating, Movie)
        .join(Movie, Rating.movie_id == Movie.id)
        .filter(Rating.user_id == user_id)
        .all()
    )
    rated_movie_ids = {rating.movie_id for rating, _ in rated_rows}
    user_ratings = [
        {
            "title": movie.title,
            "rating": rating.score,
            "genres": movie.genres or [],
            "language": movie.language,
            "year": movie.release_year,
        }
        for rating, movie in rated_rows
    ]

    candidates = (
        db.query(Movie)
        .filter(Movie.id.notin_(rated_movie_ids))
        .order_by(desc(Movie.average_rating))
        .limit(30)
        .all()
    )
    candidate_movies = [
        {
            "id": m.id,
            "title": m.title,
            "genres": m.genres or [],
            "language": m.language,
            "year": m.release_year,
            "average_rating": m.average_rating,
        }
        for m in candidates
    ]

    try:
        result = ai_agent.build_recommendations(user_ratings, candidate_movies)
    except Exception as e:
        _ai_error(e)

    # Enrich recommendations with full movie data
    enriched_recs = []
    for rec in result.get("recommendations", []):
        movie_id = rec.get("movie_id")
        movie = db.query(Movie).filter(Movie.id == movie_id).first() if movie_id else None
        enriched_recs.append({
            **rec,
            "average_rating": movie.average_rating if movie else None,
            "genres": movie.genres if movie else [],
            "poster_url": movie.poster_url if movie else None,
        })

    return {
        "user_id": user_id,
        "username": user.username,
        "rated_movie_count": len(rated_movie_ids),
        "taste_profile": result.get("taste_profile"),
        "recommendations": enriched_recs,
    }


# ---------------------------------------------------------------------------
# 5. Six Degrees Narrator
# ---------------------------------------------------------------------------

@router.get("/six-degrees/{person_a_id}/{person_b_id}/story")
def six_degrees_story(
    person_a_id: int,
    person_b_id: int,
    db: Session = Depends(get_db)
):
    """Run Six Degrees BFS and narrate the connection as an engaging story."""
    person_a = db.query(Person).filter(Person.id == person_a_id).first()
    person_b = db.query(Person).filter(Person.id == person_b_id).first()
    if not person_a or not person_b:
        raise HTTPException(status_code=404, detail="One or both people not found")

    bfs = find_connection(db, person_a_id, person_b_id)

    try:
        narrative = ai_agent.narrate_six_degrees(
            person_a.name,
            person_b.name,
            bfs.get("degrees", -1),
            bfs.get("path", [])
        )
    except Exception as e:
        _ai_error(e)

    return {
        "person_a": {"id": person_a_id, "name": person_a.name},
        "person_b": {"id": person_b_id, "name": person_b.name},
        "found": bfs.get("found", False),
        "degrees": bfs.get("degrees", -1),
        "path": bfs.get("path", []),
        **narrative,
    }
