"""
AI Agent service — wraps Ollama (local LLM) calls for CineDB's AI features.
No paid API keys required. Runs entirely on-device via Ollama.

Setup:
    brew install ollama
    ollama serve
    ollama pull llama3.2:3b   # fast model (most features)
    ollama pull llama3.1:8b   # smart model (chatbot tool-use, comparison, career)
"""
import json
import os
from typing import Optional

from openai import OpenAI

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
MODEL_FAST  = os.getenv("OLLAMA_MODEL_FAST",  "llama3.2:3b")
MODEL_SMART = os.getenv("OLLAMA_MODEL_SMART", "llama3.1:8b")

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
    return _client


def _call(system: str, user: str, max_tokens: int = 1024, smart: bool = False) -> str:
    model = MODEL_SMART if smart else MODEL_FAST
    resp = _get_client().chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )
    return resp.choices[0].message.content or ""


def _parse_json(raw: str) -> dict:
    start = raw.find("{")
    end   = raw.rfind("}") + 1
    if start == -1 or end == 0:
        return {}
    return json.loads(raw[start:end])


# ---------------------------------------------------------------------------
# 1. Natural Language Search (existing)
# ---------------------------------------------------------------------------

def parse_nl_search(query: str) -> dict:
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
}"""
    raw = _call(system, f"Search query: {query}", max_tokens=300)
    try:
        data = _parse_json(raw)
        return {"interpretation": data.get("interpretation", query), "filters": data.get("filters", {})}
    except Exception:
        return {"interpretation": query, "filters": {}}


# ---------------------------------------------------------------------------
# 2. Review Insights (existing)
# ---------------------------------------------------------------------------

def synthesize_review_insights(movie_title: str, reviews: list[dict]) -> dict:
    if not reviews:
        return {"summary": "No reviews available yet.", "pros": [], "cons": [],
                "consensus": "Not enough data.", "sentiment": "unknown", "critic_quote": None}

    reviews_text = "\n".join(
        f"[{r['username']} | {r['rating']}/10 | {r['helpful_votes']} helpful votes]: {r['text']}"
        for r in reviews
    )
    system = """You are a film critic synthesizer. Analyze user reviews and produce structured insights.
Return ONLY valid JSON:
{"summary":"2-3 sentence overview","pros":["s1","s2","s3"],"cons":["w1","w2"],"consensus":"one punchy sentence","sentiment":"positive|mixed|negative","critic_quote":"most insightful line"}"""
    raw = _call(system, f"Movie: {movie_title}\n\nReviews:\n{reviews_text}", max_tokens=500)
    try:
        return _parse_json(raw)
    except Exception:
        return {"summary": "Could not synthesize reviews.", "pros": [], "cons": [],
                "consensus": "Unavailable.", "sentiment": "unknown", "critic_quote": None}


# ---------------------------------------------------------------------------
# 3. Personalized Recommendations (existing)
# ---------------------------------------------------------------------------

def build_recommendations(user_ratings: list[dict], candidate_movies: list[dict]) -> dict:
    if not user_ratings:
        return {"taste_profile": "No rating history found. Start rating movies!", "recommendations": []}

    rated_text = "\n".join(
        f"- {r['title']} ({r['year']}, {r['language']}, {r['genres']}) → rated {r['rating']}/10"
        for r in user_ratings
    )
    candidates_text = "\n".join(
        f"[id={m['id']}] {m['title']} ({m['year']}, {m['language']}, {m['genres']}) avg={m['average_rating']}"
        for m in candidate_movies
    )
    system = """You are a personalized movie recommendation AI. Analyze rating history and recommend unrated movies.
Return ONLY valid JSON:
{"taste_profile":"2-3 sentence description","recommendations":[{"movie_id":123,"title":"Title","reason":"one sentence","match_score":9.2}]}
Pick 5 best matches. Only use ids from the candidates list."""
    raw = _call(system, f"Rated:\n{rated_text}\n\nCandidates:\n{candidates_text}", max_tokens=700, smart=True)
    try:
        return _parse_json(raw)
    except Exception:
        return {"taste_profile": "Unable to analyze taste.", "recommendations": []}


# ---------------------------------------------------------------------------
# 4. Six Degrees Narrator (existing)
# ---------------------------------------------------------------------------

def narrate_six_degrees(person_a: str, person_b: str, degrees: int, path: list[dict]) -> dict:
    if not path or degrees < 0:
        return {"degrees": -1, "story": f"No connection found between {person_a} and {person_b}.", "fun_fact": None}
    if degrees == 0:
        return {"degrees": 0, "story": f"{person_a} is the same person!", "fun_fact": None}

    chain = "\n".join(
        f"{path[i]['person_name']} → [{path[i+1].get('connected_via_movie_title','a shared film')}] → {path[i+1]['person_name']}"
        for i in range(len(path) - 1)
    )
    system = """You are a film historian. Turn a Six Degrees connection into an engaging narrative.
Return ONLY valid JSON: {"story":"3-4 sentence narrative","fun_fact":"one surprising trivia fact"}"""
    raw = _call(system, f"Connection between {person_a} and {person_b} ({degrees} degrees):\n{chain}", max_tokens=400)
    try:
        data = _parse_json(raw)
        return {"degrees": degrees, "story": data.get("story", ""), "fun_fact": data.get("fun_fact")}
    except Exception:
        return {"degrees": degrees, "story": " → ".join(p["person_name"] for p in path), "fun_fact": None}


# ---------------------------------------------------------------------------
# 5. Movie DNA (existing)
# ---------------------------------------------------------------------------

def analyze_movie_dna(movie: dict, cast_crew: list[dict], similar_titles: list[str]) -> dict:
    cast_text = ", ".join(
        f"{c['name']} ({c['role_type']})" + (f" as {c['character_name']}" if c.get("character_name") else "")
        for c in cast_crew[:8]
    )
    system = """You are a film analyst creating a Movie DNA fingerprint.
Return ONLY valid JSON:
{"themes":["t1","t2","t3"],"mood":"emotional atmosphere","audience":"who will love this","why_watch":"compelling reason","avoid_if":"honest reason to skip","dna_tags":["tag1","tag2","tag3","tag4","tag5"]}"""
    prompt = f"Movie: {movie['title']} ({movie['year']}) | {movie['language']} | {', '.join(movie['genres'])}\nPlot: {movie['plot_summary']}\nCast: {cast_text}\nSimilar: {', '.join(similar_titles[:5])}"
    raw = _call(system, prompt, max_tokens=500)
    try:
        return _parse_json(raw)
    except Exception:
        return {"themes": [], "mood": "N/A", "audience": "General", "why_watch": "Notable film.",
                "avoid_if": "N/A", "dna_tags": movie["genres"]}


# ---------------------------------------------------------------------------
# 6. Mood → Movie Discovery (NEW)
# ---------------------------------------------------------------------------

def mood_to_movies(mood_text: str, movies: list[dict]) -> dict:
    movies_text = "\n".join(
        f"[id={m['id']}] {m['title']} ({m['year']}, {m['language']}, {m['genres']}, rating={m['average_rating']})"
        for m in movies
    )
    system = """You are a mood-based movie concierge. Match a user's emotional state to perfect movies from a list.
Return ONLY valid JSON:
{"mood_interpretation":"what the user is feeling/wanting","picks":[{"movie_id":1,"title":"Title","why_fits_mood":"one sentence"}]}
Pick 4-6 best matches. Only use movie_ids from the list provided."""
    raw = _call(system, f"User mood: {mood_text}\n\nMovies:\n{movies_text}", max_tokens=600)
    try:
        return _parse_json(raw)
    except Exception:
        return {"mood_interpretation": mood_text, "picks": []}


# ---------------------------------------------------------------------------
# 7. AI Movie Comparison (NEW)
# ---------------------------------------------------------------------------

def compare_movies(movie_a: dict, movie_b: dict) -> dict:
    def fmt(m):
        return f"{m['title']} ({m['year']}, {m['language']}, {m['genres']}, rating={m['average_rating']})\nPlot: {m['plot_summary']}"

    system = """You are a film critic doing a side-by-side analysis of two movies.
Return ONLY valid JSON:
{"themes_a":["t1","t2"],"themes_b":["t1","t2"],"tone_a":"tone description","tone_b":"tone description","better_for_a":"who Movie A suits best","better_for_b":"who Movie B suits best","similarities":["s1","s2"],"verdict":"Watch A if ___, watch B if ___"}"""
    raw = _call(system, f"Movie A:\n{fmt(movie_a)}\n\nMovie B:\n{fmt(movie_b)}", max_tokens=600, smart=True)
    try:
        return _parse_json(raw)
    except Exception:
        return {"themes_a": [], "themes_b": [], "tone_a": "", "tone_b": "",
                "better_for_a": "", "better_for_b": "", "similarities": [], "verdict": ""}


# ---------------------------------------------------------------------------
# 8. Watchlist AI Prioritizer (NEW)
# ---------------------------------------------------------------------------

def prioritize_watchlist(watchlist: list[dict], user_ratings: list[dict], mood: str = "") -> dict:
    wl_text = "\n".join(
        f"[id={m['id']}] {m['title']} ({m['year']}, {m['language']}, {m['genres']})"
        for m in watchlist
    )
    taste_text = "\n".join(
        f"- {r['title']} → {r['rating']}/10"
        for r in user_ratings[:10]
    )
    mood_line = f"Current mood: {mood}" if mood else ""
    system = """You are a watch-list prioritizer. Order movies by how much the user will enjoy them right now.
Return ONLY valid JSON:
{"top_pick":{"movie_id":1,"title":"Title","tonight_reason":"why watch this tonight"},"ranked":[{"movie_id":1,"title":"Title","rank":1,"reason":"one sentence"}]}
Use only movie_ids from the watchlist. Rank all items."""
    raw = _call(system, f"Watchlist:\n{wl_text}\n\nUser taste (recent ratings):\n{taste_text}\n{mood_line}", max_tokens=700)
    try:
        return _parse_json(raw)
    except Exception:
        return {"top_pick": None, "ranked": []}


# ---------------------------------------------------------------------------
# 9. Director / Actor Career Lens (NEW)
# ---------------------------------------------------------------------------

def analyze_career(person: dict, filmography: list[dict]) -> dict:
    films_text = "\n".join(
        f"- {f['movie_title']} ({f['release_year']}, {f['role_type']}, rating={f['average_rating']})"
        for f in sorted(filmography, key=lambda x: x["release_year"])
    )
    system = """You are a film historian analyzing a cinema personality's career.
Return ONLY valid JSON:
{"arc":"career arc in 2-3 sentences","signature_style":"what makes their work distinctive","themes":["recurring theme 1","theme 2","theme 3"],"peak_period":"e.g. 2010-2018","best_entry_point":"title of the best first film to watch","hidden_gem":"an underrated work from their filmography and why"}"""
    prompt = f"Person: {person['name']} (born {person.get('birth_year','?')})\nBio: {person.get('bio','')}\n\nFilmography:\n{films_text}"
    raw = _call(system, prompt, max_tokens=600, smart=True)
    try:
        return _parse_json(raw)
    except Exception:
        return {"arc": "", "signature_style": "", "themes": [], "peak_period": "",
                "best_entry_point": "", "hidden_gem": ""}


# ---------------------------------------------------------------------------
# 10. "Pitch It to Me" (NEW)
# ---------------------------------------------------------------------------

def generate_pitch(movie: dict, tone: str) -> dict:
    tone_instructions = {
        "hype":        "Write like an excited hype-man. High energy, exclamation points, make it sound unmissable.",
        "intellectual": "Write like a thoughtful film critic. Focus on themes, craft, and what the film says about the human condition.",
        "emotional":   "Write like someone who was deeply moved. Focus on the emotional journey and personal connection.",
    }
    instruction = tone_instructions.get(tone, tone_instructions["hype"])
    system = f"""You are pitching a movie to convince a skeptic to watch it. {instruction}
Return ONLY valid JSON:
{{"hook_line":"one punchy opening line (max 15 words)","pitch_text":"3-sentence pitch","closing_line":"the final sell"}}"""
    prompt = f"Movie: {movie['title']} ({movie['year']}, {movie['language']})\nGenres: {', '.join(movie['genres'])}\nPlot: {movie['plot_summary']}\nRating: {movie['average_rating']}/10"
    raw = _call(system, prompt, max_tokens=400)
    try:
        data = _parse_json(raw)
        return {"tone": tone, **data}
    except Exception:
        return {"tone": tone, "hook_line": movie["title"], "pitch_text": movie.get("plot_summary", ""), "closing_line": ""}


# ---------------------------------------------------------------------------
# 11. Hidden Gems Finder (NEW)
# ---------------------------------------------------------------------------

def find_hidden_gems(user_ratings: list[dict], candidates: list[dict]) -> dict:
    taste_text = "\n".join(f"- {r['title']} → {r['rating']}/10" for r in user_ratings[:10])
    gems_text = "\n".join(
        f"[id={m['id']}] {m['title']} ({m['year']}, {m['language']}, {m['genres']}, avg={m['average_rating']}, votes={m['rating_count']})"
        for m in candidates
    )
    system = """You are a hidden gems expert. Find underrated movies that a specific user would love.
Return ONLY valid JSON:
{"gems":[{"movie_id":1,"title":"Title","gem_reason":"why it's underrated","why_for_you":"why this user specifically will love it","hidden_score":8.5}]}
Return 4-5 gems. Only use movie_ids from the candidates list."""
    raw = _call(system, f"User taste:\n{taste_text}\n\nCandidate hidden gems:\n{gems_text}", max_tokens=600)
    try:
        return _parse_json(raw)
    except Exception:
        return {"gems": []}


# ---------------------------------------------------------------------------
# 12. Vibe Card (NEW)
# ---------------------------------------------------------------------------

def generate_vibe_card(movie: dict, reviews_sample: list[str]) -> dict:
    reviews_text = " | ".join(reviews_sample[:5]) if reviews_sample else "No reviews available."
    system = """You are a movie vibe analyst. Describe the emotional experience of watching this film — no spoilers, just vibes.
Return ONLY valid JSON:
{"opening":"vibe of the first act","midpoint_shift":"how the tone changes","ending_feel":"emotional state you'll be in after","pace":"e.g. Slow burn → explosive finale","watch_when":"ideal mood/occasion to watch this","warning":"honest heads-up (e.g. Have tissues ready / Don't watch alone at night)","vibe_color":"one CSS color hex that represents this film's mood"}"""
    prompt = f"Movie: {movie['title']} ({movie['year']})\nGenres: {', '.join(movie['genres'])}\nPlot: {movie['plot_summary']}\nSample reviews: {reviews_text}"
    raw = _call(system, prompt, max_tokens=500)
    try:
        return _parse_json(raw)
    except Exception:
        return {"opening": "", "midpoint_shift": "", "ending_feel": "", "pace": "",
                "watch_when": "", "warning": "", "vibe_color": "#1a1a2e"}


# ---------------------------------------------------------------------------
# 13. What's Missing From Your Cinema Diet (NEW)
# ---------------------------------------------------------------------------

def find_blind_spots(gaps: list[dict], all_movies: list[dict], user_ratings: list[dict]) -> dict:
    gaps_text = "\n".join(f"- {g['category']}: {g['value']} (you have {g['count']} ratings here)" for g in gaps)
    taste_text = "\n".join(f"- {r['title']} → {r['rating']}/10" for r in user_ratings[:8])
    movies_text = "\n".join(
        f"[id={m['id']}] {m['title']} ({m['year']}, {m['language']}, {m['genres']})"
        for m in all_movies
    )
    system = """You are a cinema diet analyst. For each gap in a user's viewing history, pick one perfect entry-point movie.
Return ONLY valid JSON:
{"blind_spots":[{"category":"genre|language|decade","value":"e.g. Musical","pick_movie_id":1,"pick_title":"Title","why_start_here":"one sentence on why this is the perfect entry point"}]}
Only use movie_ids from the movies list."""
    raw = _call(system, f"Gaps:\n{gaps_text}\n\nUser taste:\n{taste_text}\n\nAvailable movies:\n{movies_text}", max_tokens=700)
    try:
        return _parse_json(raw)
    except Exception:
        return {"blind_spots": []}


# ---------------------------------------------------------------------------
# 14. AI Trivia Generator (NEW)
# ---------------------------------------------------------------------------

def generate_trivia(movie: dict, cast_crew: list[dict]) -> dict:
    cast_text = ", ".join(f"{c['name']} ({c['role_type']})" for c in cast_crew[:10])
    system = """You are a movie trivia master. Generate 5 multiple-choice questions about this film.
Mix question types: cast, crew, plot facts, production details.
Return ONLY valid JSON:
{"questions":[{"question":"Question text?","options":["A","B","C","D"],"correct_index":0,"explanation":"why this is correct"}]}
correct_index is 0-3. Make wrong answers plausible. Base questions strictly on facts provided."""
    prompt = f"Movie: {movie['title']} ({movie['year']}, {movie['language']})\nGenres: {', '.join(movie['genres'])}\nPlot: {movie['plot_summary']}\nRuntime: {movie.get('runtime_minutes','?')} min\nCast/Crew: {cast_text}"
    raw = _call(system, prompt, max_tokens=800)
    try:
        return _parse_json(raw)
    except Exception:
        return {"questions": []}


# ---------------------------------------------------------------------------
# 15. Era / Decade Analysis (NEW)
# ---------------------------------------------------------------------------

def analyze_era(decade: int, movies_in_decade: list[dict], all_stats: dict) -> dict:
    films_text = "\n".join(
        f"- {m['title']} ({m['year']}, {m['language']}, {m['genres']}, rating={m['average_rating']})"
        for m in movies_in_decade
    )
    system = """You are a film historian analyzing a decade of cinema.
Return ONLY valid JSON:
{"narrative":"3-4 sentence overview of this era's cinema","dominant_themes":["t1","t2","t3"],"defining_film":"title of the most representative film of this era","style_notes":"what was cinematically distinctive","cultural_context":"what was happening in the world that influenced these films"}"""
    prompt = f"Decade: {decade}s\nFilms from this era in our database:\n{films_text}\nOverall DB stats: {json.dumps(all_stats)}"
    raw = _call(system, prompt, max_tokens=600, smart=True)
    try:
        return _parse_json(raw)
    except Exception:
        return {"narrative": "", "dominant_themes": [], "defining_film": "", "style_notes": "", "cultural_context": ""}


# ---------------------------------------------------------------------------
# 16. Watch Party Planner (NEW)
# ---------------------------------------------------------------------------

def plan_watch_party(group_type: str, mood: str, avoid_genres: list[str], all_movies: list[dict]) -> dict:
    movies_text = "\n".join(
        f"[id={m['id']}] {m['title']} ({m['year']}, {m['language']}, {m['genres']}, rating={m['average_rating']}, cert={m['certificate']})"
        for m in all_movies
    )
    avoid_text = f"Avoid these genres: {', '.join(avoid_genres)}" if avoid_genres else ""
    system = """You are a watch party planner. Pick the perfect movie for a group to watch together.
Return ONLY valid JSON:
{"pick_movie_id":1,"pick_title":"Title","runner_up_movie_id":2,"runner_up_title":"Title","why_perfect":"2 sentences on why this film works for this group","conversation_starters":["question 1","question 2","question 3"]}
Only use movie_ids from the list."""
    prompt = f"Group type: {group_type}\nMood/vibe: {mood or 'any'}\n{avoid_text}\n\nMovies:\n{movies_text}"
    raw = _call(system, prompt, max_tokens=500)
    try:
        return _parse_json(raw)
    except Exception:
        return {"pick_movie_id": None, "pick_title": "", "runner_up_movie_id": None,
                "runner_up_title": "", "why_perfect": "", "conversation_starters": []}
