"""
AI Chatbot service with live DB tool calling.
The LLM can call DB functions in real-time to answer any question about CineDB.
Uses llama3.1:8b via Ollama (supports tool/function calling).
"""
import json
import os
import uuid
from typing import Any

from openai import OpenAI
from sqlalchemy.orm import Session

from app.models import Movie, Person, Credit, Rating, Review, User
from app.models.watchlist import WatchlistItem
from sqlalchemy import desc

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
MODEL_SMART     = os.getenv("OLLAMA_MODEL_SMART", "llama3.1:8b")

# In-memory session store: session_id → list of messages
_sessions: dict[str, list[dict]] = {}

SYSTEM_PROMPT = """You are CineBot, a knowledgeable and friendly AI assistant for CineDB — a movie database featuring Indian and international cinema. You have access to real-time database tools to look up movies, people, ratings, watchlists, and more.

Always use tools to fetch actual data before answering questions about specific movies, people, or user data. Be conversational, enthusiastic about cinema, and concise. If a user asks to do something (like add to watchlist), confirm what you've done."""

# ---------------------------------------------------------------------------
# Tool definitions (JSON schema for the LLM)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_movies",
            "description": "Search movies by title, genre, language, year range, or minimum rating",
            "parameters": {
                "type": "object",
                "properties": {
                    "title":      {"type": "string",  "description": "Partial movie title"},
                    "genre":      {"type": "string",  "description": "Genre (Action/Drama/Comedy/Thriller/Romance/Biography/History/Sci-Fi/Sport/Musical/Adventure/Family/Crime)"},
                    "language":   {"type": "string",  "description": "Language (Hindi/Tamil/Telugu/English)"},
                    "year_min":   {"type": "integer", "description": "Minimum release year"},
                    "year_max":   {"type": "integer", "description": "Maximum release year"},
                    "min_rating": {"type": "number",  "description": "Minimum average rating (0-10)"},
                    "limit":      {"type": "integer", "description": "Max results (default 5)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_movie_detail",
            "description": "Get full details of a specific movie by its ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "movie_id": {"type": "integer", "description": "The movie ID"},
                },
                "required": ["movie_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_rated",
            "description": "Get the top-rated movies in the database",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Number of movies (default 5)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_trending",
            "description": "Get currently trending movies (most recently rated)",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Number of movies (default 5)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_people",
            "description": "Search for actors, directors, or other film personalities by name",
            "parameters": {
                "type": "object",
                "properties": {
                    "name":  {"type": "string",  "description": "Person's name (partial match)"},
                    "limit": {"type": "integer", "description": "Max results (default 5)"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_person_detail",
            "description": "Get details and filmography for a specific person by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "person_id": {"type": "integer", "description": "The person ID"},
                },
                "required": ["person_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_watchlist",
            "description": "Get a user's watchlist",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "The user ID"},
                },
                "required": ["user_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_ratings",
            "description": "Get all movies a user has rated",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "The user ID"},
                },
                "required": ["user_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_movie_reviews",
            "description": "Get user reviews for a specific movie",
            "parameters": {
                "type": "object",
                "properties": {
                    "movie_id": {"type": "integer", "description": "The movie ID"},
                    "limit":    {"type": "integer", "description": "Max reviews (default 5)"},
                },
                "required": ["movie_id"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Tool execution — each calls the DB directly
# ---------------------------------------------------------------------------

def _exec_tool(name: str, args: dict, db: Session) -> Any:
    if name == "search_movies":
        q = db.query(Movie)
        if args.get("title"):    q = q.filter(Movie.title.ilike(f"%{args['title']}%"))
        if args.get("genre"):    q = q.filter(Movie.genres.any(args["genre"]))
        if args.get("language"): q = q.filter(Movie.language.ilike(f"%{args['language']}%"))
        if args.get("year_min"): q = q.filter(Movie.release_year >= args["year_min"])
        if args.get("year_max"): q = q.filter(Movie.release_year <= args["year_max"])
        if args.get("min_rating"): q = q.filter(Movie.average_rating >= args["min_rating"])
        limit = min(args.get("limit", 5), 10)
        movies = q.order_by(desc(Movie.average_rating)).limit(limit).all()
        return [{"id": m.id, "title": m.title, "year": m.release_year, "language": m.language,
                 "genres": m.genres, "rating": m.average_rating, "rating_count": m.rating_count} for m in movies]

    elif name == "get_movie_detail":
        m = db.query(Movie).filter(Movie.id == args["movie_id"]).first()
        if not m: return {"error": "Movie not found"}
        credits = db.query(Credit).filter(Credit.movie_id == m.id).all()
        cast = []
        for c in credits:
            p = db.query(Person).filter(Person.id == c.person_id).first()
            if p: cast.append({"name": p.name, "role": c.role_type, "character": c.character_name})
        return {"id": m.id, "title": m.title, "year": m.release_year, "language": m.language,
                "genres": m.genres, "rating": m.average_rating, "rating_count": m.rating_count,
                "plot": m.plot_summary, "runtime": m.runtime_minutes, "certificate": m.certificate,
                "cast_crew": cast[:8]}

    elif name == "get_top_rated":
        limit = min(args.get("limit", 5), 10)
        movies = db.query(Movie).filter(Movie.rating_count >= 3).order_by(desc(Movie.average_rating)).limit(limit).all()
        return [{"id": m.id, "title": m.title, "year": m.release_year, "rating": m.average_rating} for m in movies]

    elif name == "get_trending":
        limit = min(args.get("limit", 5), 10)
        from sqlalchemy import func
        recent = (db.query(Rating.movie_id, func.count(Rating.id).label("cnt"))
                  .group_by(Rating.movie_id).order_by(desc("cnt")).limit(limit).all())
        result = []
        for movie_id, cnt in recent:
            m = db.query(Movie).filter(Movie.id == movie_id).first()
            if m: result.append({"id": m.id, "title": m.title, "year": m.release_year, "rating": m.average_rating, "recent_ratings": cnt})
        return result

    elif name == "search_people":
        limit = min(args.get("limit", 5), 10)
        people = db.query(Person).filter(Person.name.ilike(f"%{args['name']}%")).limit(limit).all()
        return [{"id": p.id, "name": p.name, "birth_year": p.birth_year, "bio": (p.bio or "")[:200]} for p in people]

    elif name == "get_person_detail":
        p = db.query(Person).filter(Person.id == args["person_id"]).first()
        if not p: return {"error": "Person not found"}
        credits = db.query(Credit).filter(Credit.person_id == p.id).all()
        films = []
        for c in credits:
            m = db.query(Movie).filter(Movie.id == c.movie_id).first()
            if m: films.append({"title": m.title, "year": m.release_year, "role": c.role_type, "rating": m.average_rating})
        return {"id": p.id, "name": p.name, "birth_year": p.birth_year, "bio": p.bio, "filmography": films}

    elif name == "get_user_watchlist":
        items = db.query(WatchlistItem).filter(WatchlistItem.user_id == args["user_id"]).all()
        result = []
        for item in items:
            m = db.query(Movie).filter(Movie.id == item.movie_id).first()
            if m: result.append({"id": m.id, "title": m.title, "year": m.release_year, "rating": m.average_rating})
        return result

    elif name == "get_user_ratings":
        rows = db.query(Rating, Movie).join(Movie, Rating.movie_id == Movie.id).filter(Rating.user_id == args["user_id"]).all()
        return [{"title": m.title, "year": m.release_year, "score": r.score, "movie_id": m.id} for r, m in rows]

    elif name == "get_movie_reviews":
        limit = min(args.get("limit", 5), 10)
        rows = db.query(Review, User.username).join(User, Review.user_id == User.id).filter(Review.movie_id == args["movie_id"]).limit(limit).all()
        return [{"username": u, "rating": r.rating, "text": r.text, "helpful_votes": r.helpful_votes} for r, u in rows]

    return {"error": f"Unknown tool: {name}"}


# ---------------------------------------------------------------------------
# Main chat function
# ---------------------------------------------------------------------------

def chat(message: str, session_id: str, user_id: int, db: Session) -> dict:
    if session_id not in _sessions:
        _sessions[session_id] = []

    history = _sessions[session_id]
    history.append({"role": "user", "content": message})

    client   = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
    tools_used = []

    # Tool-calling loop (max 5 rounds to prevent infinite loops)
    for _ in range(5):
        resp = client.chat.completions.create(
            model=MODEL_SMART,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        msg = resp.choices[0].message

        if not msg.tool_calls:
            # Final answer
            reply = msg.content or "I'm not sure how to answer that."
            history.append({"role": "assistant", "content": reply})
            return {"reply": reply, "tools_used": tools_used, "session_id": session_id}

        # Execute each tool call
        messages.append({"role": "assistant", "content": msg.content, "tool_calls": [
            {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in msg.tool_calls
        ]})

        for tc in msg.tool_calls:
            args   = json.loads(tc.function.arguments)
            result = _exec_tool(tc.function.name, args, db)
            tools_used.append({"tool": tc.function.name, "args": args})
            messages.append({
                "role":         "tool",
                "tool_call_id": tc.id,
                "content":      json.dumps(result),
            })

    # Fallback if loop exhausted
    return {"reply": "I looked up some data but couldn't form a complete answer. Try rephrasing?",
            "tools_used": tools_used, "session_id": session_id}


def new_session() -> str:
    return str(uuid.uuid4())


def clear_session(session_id: str) -> None:
    _sessions.pop(session_id, None)
