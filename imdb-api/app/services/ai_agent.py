"""
AI Agent service — wraps Claude API calls for CineDB's intelligent features.
All functions return dicts ready for JSON serialization.
"""
import json
import os
from typing import Optional

import anthropic

MODEL = "claude-haiku-4-5-20251001"
_client: Optional[anthropic.Anthropic] = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def _call(system: str, user: str, max_tokens: int = 1024) -> str:
    client = _get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text


# ---------------------------------------------------------------------------
# 1. Natural Language Search
# ---------------------------------------------------------------------------

def parse_nl_search(query: str) -> dict:
    """
    Parse a natural-language movie search query into structured filters.
    Returns: {interpretation, filters: {title, genre, language, year_min, year_max, min_rating, certificate}}
    """
    system = """You are a movie search assistant for CineDB. Convert a natural language query into structured search filters.

Return ONLY valid JSON with this exact shape (omit fields that don't apply):
{
  "interpretation": "one-sentence summary of what the user wants",
  "filters": {
    "title": "partial title if mentioned",
    "genre": "single genre (Action/Drama/Comedy/Thriller/Romance/Biography/History/Sci-Fi/Sport/Musical/Adventure/Family/Crime)",
    "language": "Hindi or Tamil or Telugu or English etc.",
    "year_min": 1900,
    "year_max": 2030,
    "min_rating": 7.0,
    "certificate": "U or UA or A"
  }
}

Available genres: Action, Drama, Comedy, Thriller, Romance, Biography, History, Sci-Fi, Sport, Musical, Adventure, Family, Crime
Available languages: Hindi, Tamil, Telugu, English"""

    raw = _call(system, f"Search query: {query}", max_tokens=300)
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        data = json.loads(raw[start:end])
        return {
            "interpretation": data.get("interpretation", query),
            "filters": data.get("filters", {})
        }
    except Exception:
        return {"interpretation": query, "filters": {}}


# ---------------------------------------------------------------------------
# 2. Review Insights
# ---------------------------------------------------------------------------

def synthesize_review_insights(movie_title: str, reviews: list[dict]) -> dict:
    """
    Given a movie title and list of reviews, synthesize insights.
    reviews: [{username, rating, text, helpful_votes}]
    Returns: {summary, pros, cons, consensus, sentiment, critic_quote}
    """
    if not reviews:
        return {
            "summary": "No reviews available yet.",
            "pros": [],
            "cons": [],
            "consensus": "Not enough data to form a consensus.",
            "sentiment": "unknown",
            "critic_quote": None
        }

    reviews_text = "\n".join(
        f"[{r['username']} | {r['rating']}/10 | {r['helpful_votes']} helpful votes]: {r['text']}"
        for r in reviews
    )

    system = """You are a film critic synthesizer for CineDB. Analyze user reviews and produce structured insights.

Return ONLY valid JSON with this exact shape:
{
  "summary": "2-3 sentence overview of critical reception",
  "pros": ["strength 1", "strength 2", "strength 3"],
  "cons": ["weakness 1", "weakness 2"],
  "consensus": "One punchy sentence capturing the overall verdict",
  "sentiment": "positive" or "mixed" or "negative",
  "critic_quote": "The single most insightful or quotable line from any review"
}"""

    prompt = f"Movie: {movie_title}\n\nReviews:\n{reviews_text}"
    raw = _call(system, prompt, max_tokens=500)
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return {
            "summary": "Could not synthesize reviews at this time.",
            "pros": [],
            "cons": [],
            "consensus": "Analysis unavailable.",
            "sentiment": "unknown",
            "critic_quote": None
        }


# ---------------------------------------------------------------------------
# 3. Personalized Recommendations
# ---------------------------------------------------------------------------

def build_recommendations(user_ratings: list[dict], candidate_movies: list[dict]) -> dict:
    """
    Given a user's rating history and candidate movies, return personalized picks.
    user_ratings: [{title, rating, genres, language, year}]
    candidate_movies: [{id, title, genres, language, year, average_rating}]
    Returns: {taste_profile, recommendations: [{movie_id, title, reason, match_score}]}
    """
    if not user_ratings:
        return {
            "taste_profile": "No rating history found. Start rating movies to get personalized picks!",
            "recommendations": []
        }

    rated_text = "\n".join(
        f"- {r['title']} ({r['year']}, {r['language']}, {r['genres']}) → rated {r['rating']}/10"
        for r in user_ratings
    )

    candidates_text = "\n".join(
        f"[id={m['id']}] {m['title']} ({m['year']}, {m['language']}, {m['genres']}) avg={m['average_rating']}"
        for m in candidate_movies
    )

    system = """You are a personalized movie recommendation AI for CineDB. Analyze a user's rating history to infer their tastes, then recommend unrated movies they'd love.

Return ONLY valid JSON with this exact shape:
{
  "taste_profile": "2-3 sentence description of this user's cinematic taste",
  "recommendations": [
    {
      "movie_id": 123,
      "title": "Movie Title",
      "reason": "One sentence explaining why this matches their taste",
      "match_score": 9.2
    }
  ]
}

Pick the 5 best matches. match_score is 0-10. Only recommend from the candidates list using their exact id values."""

    prompt = f"User's rated movies:\n{rated_text}\n\nCandidate movies to recommend from:\n{candidates_text}"
    raw = _call(system, prompt, max_tokens=700)
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return {
            "taste_profile": "Unable to analyze taste profile at this time.",
            "recommendations": []
        }


# ---------------------------------------------------------------------------
# 4. Six Degrees Narrator
# ---------------------------------------------------------------------------

def narrate_six_degrees(person_a: str, person_b: str, degrees: int, path: list[dict]) -> dict:
    """
    Turn a Six Degrees BFS path into a compelling narrative.
    path: [{person_name, connected_via_movie_title}]
    Returns: {degrees, story, fun_fact}
    """
    if not path or degrees < 0:
        return {
            "degrees": -1,
            "story": f"No connection found between {person_a} and {person_b} within 6 degrees.",
            "fun_fact": None
        }

    if degrees == 0:
        return {
            "degrees": 0,
            "story": f"{person_a} is the same person!",
            "fun_fact": None
        }

    chain_parts = []
    for i in range(len(path) - 1):
        curr = path[i]["person_name"]
        nxt = path[i + 1]["person_name"]
        movie = path[i + 1].get("connected_via_movie_title", "a shared film")
        chain_parts.append(f"{curr} → [{movie}] → {nxt}")
    chain_text = "\n".join(chain_parts)

    system = """You are a film historian and storyteller for CineDB. Turn a Six Degrees of Separation connection into an engaging, enthusiastic narrative.

Return ONLY valid JSON with this exact shape:
{
  "story": "An engaging 3-4 sentence narrative about the connection chain, weaving in interesting facts about each person and film",
  "fun_fact": "One surprising or delightful trivia fact about any person or movie in the chain"
}"""

    prompt = f"Connection between {person_a} and {person_b} ({degrees} degree{'s' if degrees != 1 else ''}):\n\n{chain_text}"
    raw = _call(system, prompt, max_tokens=400)
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        data = json.loads(raw[start:end])
        return {
            "degrees": degrees,
            "story": data.get("story", ""),
            "fun_fact": data.get("fun_fact")
        }
    except Exception:
        simple = f"{person_a} and {person_b} are connected in {degrees} degree{'s' if degrees != 1 else ''} via: " + " → ".join(p["person_name"] for p in path)
        return {"degrees": degrees, "story": simple, "fun_fact": None}


# ---------------------------------------------------------------------------
# 5. Movie DNA — what makes this film unique
# ---------------------------------------------------------------------------

def analyze_movie_dna(movie: dict, cast_crew: list[dict], similar_titles: list[str]) -> dict:
    """
    Generate a 'Movie DNA' card: thematic fingerprint and what makes it unique.
    movie: {title, year, genres, language, plot_summary, runtime, certificate}
    cast_crew: [{name, role_type, character_name}]
    Returns: {themes, mood, audience, why_watch, avoid_if, dna_tags}
    """
    cast_text = ", ".join(
        f"{c['name']} ({c['role_type']})" + (f" as {c['character_name']}" if c.get('character_name') else "")
        for c in cast_crew[:8]
    )
    similar_text = ", ".join(similar_titles[:5]) if similar_titles else "none"

    system = """You are a film analyst for CineDB creating a 'Movie DNA' fingerprint — a unique breakdown of what makes a film tick.

Return ONLY valid JSON with this exact shape:
{
  "themes": ["theme 1", "theme 2", "theme 3"],
  "mood": "The emotional atmosphere (e.g. 'Epic and triumphant' or 'Dark and brooding')",
  "audience": "Who will love this most (e.g. 'Fans of high-octane action and brotherhood')",
  "why_watch": "The single most compelling reason to watch this film right now",
  "avoid_if": "One honest reason someone might not enjoy it",
  "dna_tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}"""

    prompt = f"""Movie: {movie['title']} ({movie['year']}) | {movie['language']} | {', '.join(movie['genres'])}
Plot: {movie['plot_summary']}
Cast/Crew: {cast_text}
Similar films: {similar_text}"""

    raw = _call(system, prompt, max_tokens=500)
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return {
            "themes": [],
            "mood": "N/A",
            "audience": "General audience",
            "why_watch": "A notable entry in world cinema.",
            "avoid_if": "Not applicable.",
            "dna_tags": movie['genres']
        }
