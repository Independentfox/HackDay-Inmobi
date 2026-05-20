"""
AI-powered endpoints for CineDB (Ollama / local LLM — no paid API keys).

Existing:
  POST /api/ai/search                        Natural language movie search
  GET  /api/ai/movies/{id}/insights          Review synthesis + sentiment
  GET  /api/ai/movies/{id}/dna               Movie DNA fingerprint
  GET  /api/ai/users/{id}/recommend          Personalized recommendations
  GET  /api/ai/six-degrees/{a}/{b}/story     Six Degrees narrative

New (12 AI-native features):
  POST /api/ai/chat                          AI Chatbot with live DB tool-calling
  POST /api/ai/mood                          Mood → Movie Discovery
  GET  /api/ai/movies/compare                AI Movie Comparison
  GET  /api/ai/users/{id}/watchlist-priority Watchlist AI Prioritizer
  GET  /api/ai/people/{id}/career-lens       Director/Actor Career Lens
  GET  /api/ai/movies/{id}/pitch             "Pitch It to Me" (3 tones)
  GET  /api/ai/users/{id}/hidden-gems        Hidden Gems Finder
  GET  /api/ai/movies/{id}/vibe              Vibe Card
  GET  /api/ai/users/{id}/blind-spots        Cinema Diet Blind Spots
  GET  /api/ai/movies/{id}/trivia            AI Trivia Generator
  GET  /api/ai/insights/era                  Era / Decade Analysis
  POST /api/ai/watch-party                   Watch Party Planner
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional

from app.database import get_db
from app.models import Movie, Person, Credit, Rating, Review, User
from app.models.watchlist import WatchlistItem
from app.services import ai_agent
from app.services import chatbot as chatbot_svc
from app.services.six_degrees import find_connection

router = APIRouter(prefix="/api/ai", tags=["AI"])

GEM_MAX_VOTES = 5   # movies with <= this many ratings are "hidden"


def _ai_error(exc: Exception):
    msg = str(exc)
    if "11434" in msg or "Connection" in msg.lower():
        raise HTTPException(
            status_code=503,
            detail="AI features require Ollama running locally. Run: ollama serve && ollama pull llama3.2:3b"
        )
    raise HTTPException(status_code=500, detail=f"AI service error: {msg}")


# ── helpers ──────────────────────────────────────────────────────────────────

def _movie_dict(m: Movie) -> dict:
    return {
        "id": m.id, "title": m.title, "year": m.release_year,
        "language": m.language, "genres": m.genres or [],
        "average_rating": m.average_rating, "rating_count": m.rating_count,
        "plot_summary": m.plot_summary, "certificate": m.certificate,
        "runtime_minutes": m.runtime_minutes, "poster_url": m.poster_url,
    }


# ── existing endpoints ────────────────────────────────────────────────────────

@router.post("/search")
def nl_search(body: dict, db: Session = Depends(get_db)):
    query = body.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query field is required")
    try:
        parsed = ai_agent.parse_nl_search(query)
    except Exception as e:
        _ai_error(e)

    filters = parsed.get("filters", {})
    q = db.query(Movie)
    if filters.get("title"):      q = q.filter(Movie.title.ilike(f"%{filters['title']}%"))
    if filters.get("genre"):      q = q.filter(Movie.genres.any(filters["genre"]))
    if filters.get("language"):   q = q.filter(Movie.language.ilike(f"%{filters['language']}%"))
    if filters.get("year_min"):   q = q.filter(Movie.release_year >= int(filters["year_min"]))
    if filters.get("year_max"):   q = q.filter(Movie.release_year <= int(filters["year_max"]))
    if filters.get("min_rating"): q = q.filter(Movie.average_rating >= float(filters["min_rating"]))
    if filters.get("certificate"): q = q.filter(Movie.certificate == filters["certificate"])
    movies = q.order_by(desc(Movie.average_rating)).limit(10).all()
    return {"query": query, "interpretation": parsed.get("interpretation"),
            "filters_applied": filters, "results": [_movie_dict(m) for m in movies], "result_count": len(movies)}


@router.get("/movies/{movie_id}/insights")
def review_insights(movie_id: int, db: Session = Depends(get_db)):
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie: raise HTTPException(404, "Movie not found")
    rows = (db.query(Review, User.username).join(User, Review.user_id == User.id)
            .filter(Review.movie_id == movie_id).order_by(desc(Review.helpful_votes)).limit(20).all())
    reviews = [{"username": u, "rating": r.rating, "text": r.text, "helpful_votes": r.helpful_votes} for r, u in rows]
    try:
        insights = ai_agent.synthesize_review_insights(movie.title, reviews)
    except Exception as e:
        _ai_error(e)
    return {"movie_id": movie_id, "movie_title": movie.title, "review_count": len(reviews), **insights}


@router.get("/movies/{movie_id}/dna")
def movie_dna(movie_id: int, db: Session = Depends(get_db)):
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie: raise HTTPException(404, "Movie not found")
    credits = db.query(Credit).filter(Credit.movie_id == movie_id).all()
    cast_crew = []
    for c in credits:
        p = db.query(Person).filter(Person.id == c.person_id).first()
        if p: cast_crew.append({"name": p.name, "role_type": c.role_type, "character_name": c.character_name})
    similar = []
    if movie.genres:
        similar = [m.title for m in db.query(Movie).filter(Movie.id != movie_id, Movie.genres.overlap(movie.genres))
                   .order_by(desc(Movie.average_rating)).limit(5).all()]
    try:
        dna = ai_agent.analyze_movie_dna(_movie_dict(movie), cast_crew, similar)
    except Exception as e:
        _ai_error(e)
    return {"movie_id": movie_id, "movie_title": movie.title, **dna}


@router.get("/users/{user_id}/recommend")
def personalized_recommendations(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(404, "User not found")
    rated_rows = db.query(Rating, Movie).join(Movie, Rating.movie_id == Movie.id).filter(Rating.user_id == user_id).all()
    rated_ids  = {r.movie_id for r, _ in rated_rows}
    user_ratings = [{"title": m.title, "rating": r.score, "genres": m.genres or [], "language": m.language, "year": m.release_year} for r, m in rated_rows]
    candidates   = db.query(Movie).filter(Movie.id.notin_(rated_ids)).order_by(desc(Movie.average_rating)).limit(30).all()
    candidate_movies = [{"id": m.id, "title": m.title, "genres": m.genres or [], "language": m.language, "year": m.release_year, "average_rating": m.average_rating} for m in candidates]
    try:
        result = ai_agent.build_recommendations(user_ratings, candidate_movies)
    except Exception as e:
        _ai_error(e)
    enriched = []
    for rec in result.get("recommendations", []):
        m = db.query(Movie).filter(Movie.id == rec.get("movie_id")).first() if rec.get("movie_id") else None
        enriched.append({**rec, "average_rating": m.average_rating if m else None, "genres": m.genres if m else [], "poster_url": m.poster_url if m else None})
    return {"user_id": user_id, "username": user.username, "rated_movie_count": len(rated_ids),
            "taste_profile": result.get("taste_profile"), "recommendations": enriched}


@router.get("/six-degrees/{person_a_id}/{person_b_id}/story")
def six_degrees_story(person_a_id: int, person_b_id: int, db: Session = Depends(get_db)):
    pa = db.query(Person).filter(Person.id == person_a_id).first()
    pb = db.query(Person).filter(Person.id == person_b_id).first()
    if not pa or not pb: raise HTTPException(404, "One or both people not found")
    bfs = find_connection(db, person_a_id, person_b_id)
    try:
        narrative = ai_agent.narrate_six_degrees(pa.name, pb.name, bfs.get("degrees", -1), bfs.get("path", []))
    except Exception as e:
        _ai_error(e)
    return {"person_a": {"id": person_a_id, "name": pa.name}, "person_b": {"id": person_b_id, "name": pb.name},
            "found": bfs.get("found", False), "degrees": bfs.get("degrees", -1), "path": bfs.get("path", []), **narrative}


# ── NEW: Chatbot ──────────────────────────────────────────────────────────────

@router.post("/chat")
def chat(body: dict, db: Session = Depends(get_db)):
    message    = body.get("message", "").strip()
    session_id = body.get("session_id") or chatbot_svc.new_session()
    user_id    = body.get("user_id", 1)
    if not message:
        raise HTTPException(400, "message field is required")
    try:
        result = chatbot_svc.chat(message, session_id, user_id, db)
    except Exception as e:
        _ai_error(e)
    return result


@router.delete("/chat/{session_id}")
def clear_chat(session_id: str):
    chatbot_svc.clear_session(session_id)
    return {"cleared": True}


# ── NEW: Mood → Movie ─────────────────────────────────────────────────────────

@router.post("/mood")
def mood_movies(body: dict, db: Session = Depends(get_db)):
    mood = body.get("mood", "").strip()
    if not mood:
        raise HTTPException(400, "mood field is required")
    all_movies = db.query(Movie).order_by(desc(Movie.average_rating)).all()
    movies_list = [_movie_dict(m) for m in all_movies]
    try:
        result = ai_agent.mood_to_movies(mood, movies_list)
    except Exception as e:
        _ai_error(e)
    picks = []
    for pick in result.get("picks", []):
        m = db.query(Movie).filter(Movie.id == pick.get("movie_id")).first()
        if m: picks.append({**pick, **_movie_dict(m)})
    return {"mood_interpretation": result.get("mood_interpretation", mood), "picks": picks}


# ── NEW: Movie Comparison ─────────────────────────────────────────────────────

@router.get("/movies/compare")
def compare_movies(a: int, b: int, db: Session = Depends(get_db)):
    ma = db.query(Movie).filter(Movie.id == a).first()
    mb = db.query(Movie).filter(Movie.id == b).first()
    if not ma or not mb: raise HTTPException(404, "One or both movies not found")
    try:
        result = ai_agent.compare_movies(_movie_dict(ma), _movie_dict(mb))
    except Exception as e:
        _ai_error(e)
    return {"movie_a": _movie_dict(ma), "movie_b": _movie_dict(mb), **result}


# ── NEW: Watchlist Prioritizer ────────────────────────────────────────────────

@router.get("/users/{user_id}/watchlist-priority")
def watchlist_priority(user_id: int, mood: Optional[str] = "", db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(404, "User not found")
    wl_items = db.query(WatchlistItem).filter(WatchlistItem.user_id == user_id).all()
    if not wl_items:
        return {"top_pick": None, "ranked": [], "message": "Watchlist is empty"}
    watchlist = []
    for item in wl_items:
        m = db.query(Movie).filter(Movie.id == item.movie_id).first()
        if m: watchlist.append(_movie_dict(m))
    rated_rows = db.query(Rating, Movie).join(Movie, Rating.movie_id == Movie.id).filter(Rating.user_id == user_id).all()
    user_ratings = [{"title": m.title, "rating": r.score} for r, m in rated_rows]
    try:
        result = ai_agent.prioritize_watchlist(watchlist, user_ratings, mood or "")
    except Exception as e:
        _ai_error(e)
    top_pick_movie = None
    if result.get("top_pick") and result["top_pick"].get("movie_id"):
        m = db.query(Movie).filter(Movie.id == result["top_pick"]["movie_id"]).first()
        if m: top_pick_movie = {**result["top_pick"], **_movie_dict(m)}
    ranked = []
    for item in result.get("ranked", []):
        m = db.query(Movie).filter(Movie.id == item.get("movie_id")).first()
        if m: ranked.append({**item, **_movie_dict(m)})
    return {"top_pick": top_pick_movie, "ranked": ranked}


# ── NEW: Career Lens ──────────────────────────────────────────────────────────

@router.get("/people/{person_id}/career-lens")
def career_lens(person_id: int, db: Session = Depends(get_db)):
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person: raise HTTPException(404, "Person not found")
    credits = db.query(Credit).filter(Credit.person_id == person_id).all()
    filmography = []
    for c in credits:
        m = db.query(Movie).filter(Movie.id == c.movie_id).first()
        if m:
            filmography.append({"movie_title": m.title, "release_year": m.release_year,
                                 "role_type": c.role_type, "average_rating": m.average_rating or 0})
    person_dict = {"name": person.name, "birth_year": person.birth_year, "bio": person.bio}
    try:
        result = ai_agent.analyze_career(person_dict, filmography)
    except Exception as e:
        _ai_error(e)
    return {"person_id": person_id, "person_name": person.name, "filmography": filmography, **result}


# ── NEW: Pitch It to Me ───────────────────────────────────────────────────────

@router.get("/movies/{movie_id}/pitch")
def pitch_movie(movie_id: int, tone: str = "hype", db: Session = Depends(get_db)):
    if tone not in ("hype", "intellectual", "emotional"):
        raise HTTPException(400, "tone must be hype, intellectual, or emotional")
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie: raise HTTPException(404, "Movie not found")
    try:
        result = ai_agent.generate_pitch(_movie_dict(movie), tone)
    except Exception as e:
        _ai_error(e)
    return {"movie_id": movie_id, "movie_title": movie.title, **result}


# ── NEW: Hidden Gems ──────────────────────────────────────────────────────────

@router.get("/users/{user_id}/hidden-gems")
def hidden_gems(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(404, "User not found")
    rated_rows = db.query(Rating, Movie).join(Movie, Rating.movie_id == Movie.id).filter(Rating.user_id == user_id).all()
    rated_ids   = {r.movie_id for r, _ in rated_rows}
    user_ratings = [{"title": m.title, "rating": r.score} for r, m in rated_rows]
    candidates  = (db.query(Movie).filter(Movie.id.notin_(rated_ids), Movie.rating_count <= GEM_MAX_VOTES,
                                          Movie.average_rating >= 7.0).all())
    if not candidates:
        candidates = db.query(Movie).filter(Movie.id.notin_(rated_ids)).order_by(Movie.rating_count).limit(10).all()
    candidate_list = [_movie_dict(m) for m in candidates]
    try:
        result = ai_agent.find_hidden_gems(user_ratings, candidate_list)
    except Exception as e:
        _ai_error(e)
    gems = []
    for gem in result.get("gems", []):
        m = db.query(Movie).filter(Movie.id == gem.get("movie_id")).first()
        if m: gems.append({**gem, **_movie_dict(m)})
    return {"user_id": user_id, "gems": gems}


# ── NEW: Vibe Card ────────────────────────────────────────────────────────────

@router.get("/movies/{movie_id}/vibe")
def vibe_card(movie_id: int, db: Session = Depends(get_db)):
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie: raise HTTPException(404, "Movie not found")
    reviews = db.query(Review).filter(Review.movie_id == movie_id).limit(5).all()
    review_texts = [r.text for r in reviews if r.text]
    try:
        result = ai_agent.generate_vibe_card(_movie_dict(movie), review_texts)
    except Exception as e:
        _ai_error(e)
    return {"movie_id": movie_id, "movie_title": movie.title, **result}


# ── NEW: Blind Spots ──────────────────────────────────────────────────────────

@router.get("/users/{user_id}/blind-spots")
def blind_spots(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(404, "User not found")
    rated_rows = db.query(Rating, Movie).join(Movie, Rating.movie_id == Movie.id).filter(Rating.user_id == user_id).all()
    user_ratings = [{"title": m.title, "rating": r.score} for r, m in rated_rows]

    # Compute gaps
    seen_genres = set(); seen_langs = set(); seen_decades = set()
    for r, m in rated_rows:
        seen_genres.update(m.genres or [])
        seen_langs.add(m.language)
        seen_decades.add((m.release_year // 10) * 10)

    all_movies = db.query(Movie).all()
    all_genres = {g for m in all_movies for g in (m.genres or [])}
    all_langs  = {m.language for m in all_movies}
    all_decades = {(m.release_year // 10) * 10 for m in all_movies}

    gaps = []
    for g in all_genres - seen_genres:
        gaps.append({"category": "genre", "value": g, "count": 0})
    for l in all_langs - seen_langs:
        gaps.append({"category": "language", "value": l, "count": 0})
    for d in all_decades - seen_decades:
        gaps.append({"category": "decade", "value": f"{d}s", "count": 0})

    if not gaps:
        return {"user_id": user_id, "blind_spots": [], "message": "Impressive! No major blind spots found."}

    all_movies_list = [_movie_dict(m) for m in all_movies if m.id not in {r.movie_id for r, _ in rated_rows}]
    try:
        result = ai_agent.find_blind_spots(gaps[:8], all_movies_list, user_ratings)
    except Exception as e:
        _ai_error(e)
    blind_spots_enriched = []
    for bs in result.get("blind_spots", []):
        m = db.query(Movie).filter(Movie.id == bs.get("pick_movie_id")).first()
        if m: blind_spots_enriched.append({**bs, "pick_movie": _movie_dict(m)})
        else: blind_spots_enriched.append(bs)
    return {"user_id": user_id, "blind_spots": blind_spots_enriched}


# ── NEW: Trivia ───────────────────────────────────────────────────────────────

@router.get("/movies/{movie_id}/trivia")
def movie_trivia(movie_id: int, db: Session = Depends(get_db)):
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie: raise HTTPException(404, "Movie not found")
    credits = db.query(Credit).filter(Credit.movie_id == movie_id).all()
    cast_crew = []
    for c in credits:
        p = db.query(Person).filter(Person.id == c.person_id).first()
        if p: cast_crew.append({"name": p.name, "role_type": c.role_type, "character_name": c.character_name})
    try:
        result = ai_agent.generate_trivia(_movie_dict(movie), cast_crew)
    except Exception as e:
        _ai_error(e)
    return {"movie_id": movie_id, "movie_title": movie.title, **result}


# ── NEW: Era Analysis ─────────────────────────────────────────────────────────

@router.get("/insights/era")
def era_analysis(decade: int = 2010, db: Session = Depends(get_db)):
    if decade not in range(1950, 2030, 10):
        raise HTTPException(400, "decade must be a multiple of 10 between 1950 and 2020")
    movies_in_decade = db.query(Movie).filter(Movie.release_year >= decade, Movie.release_year < decade + 10).all()
    if not movies_in_decade:
        return {"decade": decade, "message": "No movies in this decade in the database."}
    all_stats = {
        "total_movies": db.query(Movie).count(),
        "avg_rating_overall": db.query(func.avg(Movie.average_rating)).scalar(),
    }
    try:
        result = ai_agent.analyze_era(decade, [_movie_dict(m) for m in movies_in_decade], all_stats)
    except Exception as e:
        _ai_error(e)
    return {"decade": decade, "movie_count": len(movies_in_decade),
            "movies": [_movie_dict(m) for m in movies_in_decade], **result}


# ── NEW: Watch Party Planner ──────────────────────────────────────────────────

@router.post("/watch-party")
def watch_party(body: dict, db: Session = Depends(get_db)):
    group_type    = body.get("group_type", "friends")
    mood          = body.get("mood", "")
    avoid_genres  = body.get("avoid_genres", [])
    if group_type not in ("family", "friends", "date", "kids"):
        raise HTTPException(400, "group_type must be family, friends, date, or kids")
    all_movies = db.query(Movie).order_by(desc(Movie.average_rating)).all()
    if group_type == "kids":
        all_movies = [m for m in all_movies if m.certificate in ("U", "UA")]
    movies_list = [_movie_dict(m) for m in all_movies]
    try:
        result = ai_agent.plan_watch_party(group_type, mood, avoid_genres, movies_list)
    except Exception as e:
        _ai_error(e)
    pick = db.query(Movie).filter(Movie.id == result.get("pick_movie_id")).first() if result.get("pick_movie_id") else None
    runner_up = db.query(Movie).filter(Movie.id == result.get("runner_up_movie_id")).first() if result.get("runner_up_movie_id") else None
    return {
        "group_type": group_type,
        "pick":       {**_movie_dict(pick), "why_perfect": result.get("why_perfect", ""), "conversation_starters": result.get("conversation_starters", [])} if pick else None,
        "runner_up":  _movie_dict(runner_up) if runner_up else None,
    }
