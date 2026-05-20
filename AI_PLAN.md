# CineDB — AI-Native Transformation Plan

## LLM Stack Decision: Ollama (100% Free, Local)

No paid API keys. No cloud billing. Everything runs on-device via **Ollama**.

### Why Ollama
- Runs LLMs entirely on your laptop — no API key, no internet, no cost
- OpenAI-compatible REST API at `http://localhost:11434/v1/`
- Supports tool/function calling (required for the chatbot)
- One-command install, models download automatically on first use

### Models to use
| Purpose | Model | Pull Command |
|---|---|---|
| Chatbot + Tool Use | `llama3.1:8b` | `ollama pull llama3.1:8b` |
| Fast text generation | `llama3.2:3b` | `ollama pull llama3.2:3b` |
| Fallback / richer reasoning | `mistral:7b` | `ollama pull mistral:7b` |

### Install Ollama
```bash
# macOS
brew install ollama
ollama serve          # starts the local server on :11434

# Pull models (do this once)
ollama pull llama3.1:8b
ollama pull llama3.2:3b
```

### Connecting from Python
```python
# No new package needed — use httpx (already in requirements.txt)
# OR add openai package and point base_url at Ollama

pip install openai    # add to requirements.txt

from openai import OpenAI
llm = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
```

### Config
Add to `.env` and `.env.example`:
```
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_MODEL_FAST=llama3.2:3b
OLLAMA_MODEL_SMART=llama3.1:8b
```

---

## Architecture Overview

```
Frontend (app.js)
    │
    ▼
FastAPI Routers  (/api/ai/*)
    │
    ▼
app/services/ai_agent.py   ← replace Anthropic client with Ollama client
    │
    ▼
Ollama (localhost:11434)   ← llama3.1:8b / llama3.2:3b
    │
    ▼
PostgreSQL DB              ← chatbot reads live data via tool calls
```

**Key change:** Replace the `anthropic` client in `ai_agent.py` with the `openai` package
pointed at Ollama. All 5 existing features keep working, new features added alongside.

---

## Migration: Replace Anthropic → Ollama

### Files to change
- `app/services/ai_agent.py` — swap `anthropic.Anthropic()` for `OpenAI(base_url=OLLAMA_URL)`
- `requirements.txt` — remove `anthropic>=0.40.0`, add `openai>=1.0.0`
- `.env.example` — add Ollama config vars, remove `ANTHROPIC_API_KEY`
- `docker-compose.yml` — remove `ANTHROPIC_API_KEY` env var

### Migration todos
- [ ] Add `openai>=1.0.0` to `requirements.txt`, remove `anthropic`
- [ ] Rewrite `_get_client()` in `ai_agent.py` to use `OpenAI(base_url=..., api_key="ollama")`
- [ ] Rewrite `_call()` to use `client.chat.completions.create()`
- [ ] Update `.env.example` with Ollama vars
- [ ] Test all 5 existing endpoints still work after migration
- [ ] Update `docker-compose.yml` — add `OLLAMA_BASE_URL` env var

---

## Feature 1 — AI Chatbot with Tool Use

**The flagship feature.** Claude-style conversational assistant that can look up
anything from the live database using function/tool calling.

### What it does
User types anything in a chat window. The LLM decides which DB tools to call
(search movies, get movie detail, look up a person, check ratings, etc.),
fetches live data, and answers in natural language. Multi-turn conversation
with session memory.

### Example interactions
- *"Who directed Baahubali?"* → calls `get_movie_details(5)` → answers
- *"What are the best Telugu films?"* → calls `search_movies(language=Telugu, sort=rating)`
- *"Compare the ratings of Inception and Dangal"* → two tool calls
- *"Add Interstellar to alice's watchlist"* → calls `add_to_watchlist()`
- *"What movies does alice have in common with bob?"* → two watchlist tool calls

### Tools to expose to the LLM
```
search_movies(genre, language, year_min, year_max, min_rating, title)
get_movie_detail(movie_id)
get_person_detail(person_id)
search_people(name)
get_user_watchlist(user_id)
get_top_rated(limit)
get_trending(limit)
get_movie_reviews(movie_id)
get_user_ratings(user_id)
```

### Backend todos
- [ ] Create `app/services/chatbot.py` — tool definitions (JSON schema) for each DB function
- [ ] Implement each tool as a Python function that queries the DB
- [ ] Add tool-calling loop: LLM responds → parse tool calls → execute → feed results back → final answer
- [ ] Create `POST /api/ai/chat` endpoint in `ai.py`
  - Body: `{message: str, session_id: str, user_id: int}`
  - Response: `{reply: str, tools_used: list, session_id: str}`
- [ ] Store conversation history in-memory (dict keyed by `session_id`) so multi-turn works
- [ ] Model: `llama3.1:8b` (required for reliable tool calling)

### Frontend todos
- [ ] Add chat panel to the AI page — floating sidebar or dedicated tab
- [ ] Chat bubble UI (user messages right, AI messages left)
- [ ] Show which tools were called (e.g. "🔍 Searched movies", "📋 Checked watchlist")
- [ ] Session persistence via `localStorage` (session_id survives page refresh)
- [ ] Typing indicator while waiting for response
- [ ] "New conversation" button to reset session

---

## Feature 2 — Mood → Movie Discovery

User describes how they feel or what they want → AI maps that to movies from the DB.

### Example inputs
- *"I'm exhausted after work and need something light and funny"*
- *"I want to ugly cry tonight"*
- *"Something epic with great music for a Saturday night"*
- *"I'm with my 10-year-old, what do we watch?"*

### Backend todos
- [ ] Add `POST /api/ai/mood` endpoint
  - Body: `{mood: str, user_id?: int}`
  - AI reads the mood, maps to genre/tone/language preferences
  - Pulls matching movies from DB (filtered query)
  - Returns: `{mood_interpretation, movies: [...], why_each_fits}`
- [ ] Add `mood_to_movies(mood_text, all_movies)` function in `ai_agent.py`
- [ ] Use `llama3.2:3b` (fast, simple task)

### Frontend todos
- [ ] Add "Mood Search" input on the home page or AI tab
- [ ] Big text input: "How are you feeling tonight?"
- [ ] Results shown as movie cards with a personalised "why this fits your mood" blurb

---

## Feature 3 — AI Movie Comparison

Pick any two movies → AI generates a structured side-by-side analysis.

### What it outputs
- Thematic comparison
- Tone & style differences
- Who each film is better for
- A final verdict: "Watch X if you want ___, watch Y if you want ___"

### Backend todos
- [ ] Add `GET /api/ai/movies/compare?a={id}&b={id}` endpoint
- [ ] Fetch full detail for both movies from DB (plot, genres, cast, ratings, reviews)
- [ ] Add `compare_movies(movie_a, movie_b)` in `ai_agent.py`
- [ ] Return: `{themes_a, themes_b, tone_comparison, better_for_a, better_for_b, verdict}`
- [ ] Use `llama3.1:8b`

### Frontend todos
- [ ] "Compare" button on every movie card / detail page
- [ ] Movie picker modal: search and select a second movie
- [ ] Side-by-side comparison card UI (two columns)
- [ ] Share-able comparison result (copy URL)

---

## Feature 4 — Watchlist AI Prioritizer

AI orders your watchlist and tells you what to watch right now.

### What it does
- Reads user's watchlist + their past ratings
- Optional: takes current mood as input
- Returns watchlist ranked with a personalised reason for each pick
- Highlights what to watch TONIGHT (the top pick)

### Backend todos
- [ ] Add `GET /api/ai/users/{user_id}/watchlist-priority?mood=` endpoint
- [ ] Fetch watchlist + rating history for user from DB
- [ ] Add `prioritize_watchlist(watchlist, ratings, mood)` in `ai_agent.py`
- [ ] Return: `{top_pick: {movie, tonight_reason}, ranked_list: [{movie, priority_reason, rank}]}`
- [ ] Use `llama3.2:3b`

### Frontend todos
- [ ] "AI Sort" button on the watchlist page
- [ ] Optional mood input field above the button
- [ ] Ranked watchlist cards with AI-generated priority reasons
- [ ] Highlight the #1 pick with a "Watch Tonight" badge

---

## Feature 5 — Director / Actor Career Lens

On any person's page → AI reads their full filmography from the DB and generates a career analysis.

### What it outputs
- Career arc (early work → peak → recent)
- Recurring themes and signature style
- Best entry point (what to watch first)
- Hidden gem from their filmography

### Backend todos
- [ ] Add `GET /api/ai/people/{person_id}/career-lens` endpoint
- [ ] Fetch person + full filmography + ratings from DB
- [ ] Add `analyze_career(person, filmography)` in `ai_agent.py`
- [ ] Return: `{arc, signature_style, themes, best_entry_point, hidden_gem, peak_period}`
- [ ] Use `llama3.1:8b`

### Frontend todos
- [ ] "Career Lens" button on the person detail page (alongside existing "Six Degrees")
- [ ] Career analysis card rendered below the person hero section
- [ ] Timeline-style display of filmography with AI annotations

---

## Feature 6 — "Pitch It to Me"

For any movie → AI generates a punchy short pitch to convince a skeptic to watch it.
Three tone options so the pitch matches who you're pitching to.

### Tone options
- 🔥 **Hype** — "This is the most insane ride you'll ever take…"
- 🧠 **Intellectual** — "A meditation on grief disguised as a heist film…"
- ❤️ **Emotional** — "You will laugh, cry, and call your dad after this…"

### Backend todos
- [ ] Add `GET /api/ai/movies/{id}/pitch?tone=hype|intellectual|emotional` endpoint
- [ ] Add `generate_pitch(movie, tone)` in `ai_agent.py`
- [ ] Return: `{tone, pitch_text, hook_line}` (hook_line is the one-liner opener)
- [ ] Use `llama3.2:3b` (fast, creative task)

### Frontend todos
- [ ] "Pitch It" button on movie detail page
- [ ] Three tone selector buttons (Hype / Intellectual / Emotional)
- [ ] Pitch displayed in a stylised card with the hook_line prominent
- [ ] "Copy pitch" button (share with friends)

---

## Feature 7 — Hidden Gems Finder

AI scans the full DB for underrated movies aligned to your taste.

### Logic
- Underrated = high average rating but low rating count (people who saw it loved it)
- Cross-referenced against user's taste profile from rating history
- AI explains WHY each is a hidden gem for THIS specific user

### Backend todos
- [ ] Add `GET /api/ai/users/{user_id}/hidden-gems` endpoint
- [ ] Query: movies with `rating_count < threshold` but `average_rating > X`
- [ ] Add `find_hidden_gems(user_ratings, candidates)` in `ai_agent.py`
- [ ] Return: `{gems: [{movie, gem_reason, why_for_you, hidden_score}]}`
- [ ] Use `llama3.2:3b`

### Frontend todos
- [ ] "Hidden Gems" tab or button on the AI page
- [ ] Cards with a "💎 Hidden Gem" badge
- [ ] Show rating count (e.g. "Only 3 people have rated this") for context
- [ ] Personalised blurb: "Based on your love of Telugu epics…"

---

## Feature 8 — Vibe Card

Before you commit to a movie → AI tells you the emotional journey to expect. No spoilers. Just vibes.

### What it outputs
- Opening vibe, mid-film shift, ending feeling
- Pace description
- "Watch when you're in a ___ mood"
- Physical/emotional warning ("Have tissues ready", "Don't start this at midnight")

### Backend todos
- [ ] Add `GET /api/ai/movies/{id}/vibe` endpoint
- [ ] Add `generate_vibe_card(movie)` in `ai_agent.py` — uses plot, genres, reviews
- [ ] Return: `{opening, midpoint_shift, ending_feel, pace, watch_when, warning}`
- [ ] Use `llama3.2:3b`

### Frontend todos
- [ ] "Vibe Check" button on movie detail page (next to Pitch It)
- [ ] Stylised vibe card with an emotional arc visualisation
- [ ] Color-coded by mood (warm tones for feel-good, cool/dark for intense)

---

## Feature 9 — "What's Missing From Your Cinema Diet"

AI audits your rating history and identifies blind spots — genres, languages, eras
you haven't explored — then gives one curated pick for each gap.

### Backend todos
- [ ] Add `GET /api/ai/users/{user_id}/blind-spots` endpoint
- [ ] Compute gaps: which genres/languages/decades the user has < 2 ratings in
- [ ] Add `find_blind_spots(user_ratings, all_movies, gaps)` in `ai_agent.py`
- [ ] Return: `{gaps: [{category, category_value, pick: {movie}, why_start_here}]}`
- [ ] Use `llama3.2:3b`

### Frontend todos
- [ ] "Cinema Diet" section in the AI tab / user profile
- [ ] Gap cards: e.g. "You've never rated a Musical 🎵" + recommended movie
- [ ] Progress bar showing genre/language coverage (visual audit)
- [ ] "Add to watchlist" from each gap card

---

## Feature 10 — AI Trivia Generator

Generates a 5-question quiz about any movie from the DB. Fully dynamic from DB data.

### Question types
- Cast & crew ("Who played X in Y?")
- Production facts (year, runtime, language)
- Plot-based ("What is the central conflict of Y?")
- Cross-movie ("Which of these actors appeared in both A and B?")

### Backend todos
- [ ] Add `GET /api/ai/movies/{id}/trivia` endpoint
- [ ] Fetch movie detail + cast/crew from DB
- [ ] Add `generate_trivia(movie, cast_crew)` in `ai_agent.py`
- [ ] Return: `{questions: [{question, options: [4], correct_index, explanation}]}`
- [ ] Use `llama3.2:3b`

### Frontend todos
- [ ] "Trivia" button on movie detail page
- [ ] Interactive quiz card — one question at a time
- [ ] Score tracker + answer reveal with AI explanation
- [ ] Shareable result: "I scored 4/5 on Inception trivia!"

---

## Feature 11 — Era / Decade Analysis

AI analyses trends across the decades represented in the DB — how cinema evolved,
what themes dominated each era, and what changed.

### Backend todos
- [ ] Add `GET /api/ai/insights/era?decade=1950|1960|...|2020` endpoint
- [ ] Add `GET /api/ai/insights/evolution` endpoint (full overview)
- [ ] Query DB for movies grouped by decade with avg ratings, genres, languages
- [ ] Add `analyze_era(decade, movies_in_decade, all_stats)` in `ai_agent.py`
- [ ] Return: `{decade, dominant_genres, avg_rating, defining_films, narrative}`
- [ ] Use `llama3.1:8b`

### Frontend todos
- [ ] New "Eras" section on the Stats page
- [ ] Decade selector (1950s → 2020s)
- [ ] AI-generated narrative paragraph for each era
- [ ] Highlight the "defining film" of each decade with its poster

---

## Feature 12 — Watch Party Planner

Input: who you're watching with (family/friends/date/kids).
Output: AI picks the perfect movie from the DB that everyone will enjoy.

### Backend todos
- [ ] Add `POST /api/ai/watch-party` endpoint
  - Body: `{group_type: family|friends|date|kids, mood?: str, avoid_genres?: []}`
- [ ] Add `plan_watch_party(group_type, mood, all_movies)` in `ai_agent.py`
- [ ] Return: `{pick: {movie}, runner_up: {movie}, why_perfect, conversation_starters: [3 questions]}`
- [ ] Use `llama3.2:3b`

### Frontend todos
- [ ] "Watch Party" button/card on home page
- [ ] Group type selector (icons: 👨‍👩‍👧 Family / 👫 Date / 🎉 Friends / 👦 Kids)
- [ ] Optional mood/vibe text input
- [ ] Result: big movie card + "Why it works for your group" + 3 conversation starters
- [ ] "Try another pick" button

---

## Execution Order

Build in this sequence — each phase is independently shippable:

```
Phase 0 (foundation):  Migrate Anthropic → Ollama
Phase 1 (flagship):    Chatbot (F1) + Mood Discovery (F2)
Phase 2 (engagement):  Comparison (F3) + Watchlist Prioritizer (F4) + Career Lens (F5)
Phase 3 (discovery):   Pitch It (F6) + Hidden Gems (F7) + Vibe Card (F8)
Phase 4 (extras):      Blind Spots (F9) + Trivia (F10) + Era Analysis (F11) + Watch Party (F12)
```

---

## Master Todo Checklist

### Phase 0 — Ollama Migration
- [ ] Install Ollama locally (`brew install ollama`)
- [ ] Pull models: `ollama pull llama3.1:8b && ollama pull llama3.2:3b`
- [ ] Add `openai>=1.0.0` to `requirements.txt`, remove `anthropic>=0.40.0`
- [ ] Rewrite `ai_agent.py` `_get_client()` to use OpenAI client → Ollama base_url
- [ ] Rewrite `_call()` to use `chat.completions.create()`
- [ ] Update `.env.example` with `OLLAMA_BASE_URL`, `OLLAMA_MODEL_FAST`, `OLLAMA_MODEL_SMART`
- [ ] Remove `ANTHROPIC_API_KEY` from `docker-compose.yml` and `.env.example`
- [ ] Smoke-test all 5 existing AI endpoints still work

### Phase 1 — Chatbot + Mood Discovery
- [ ] Create `app/services/chatbot.py` with tool schemas + execution logic
- [ ] Implement all 9 DB tool functions in `chatbot.py`
- [ ] Add tool-calling loop in chatbot service
- [ ] Add `POST /api/ai/chat` endpoint
- [ ] Add in-memory session store for multi-turn conversations
- [ ] Build chat UI in `index.html` (panel/sidebar)
- [ ] Wire chat UI to `/api/ai/chat` in `app.js`
- [ ] Add tool-call indicators in chat bubbles
- [ ] Add `POST /api/ai/mood` endpoint
- [ ] Add `mood_to_movies()` in `ai_agent.py`
- [ ] Build Mood Search UI on home page

### Phase 2 — Comparison, Watchlist, Career Lens
- [ ] Add `GET /api/ai/movies/compare` endpoint
- [ ] Add `compare_movies()` in `ai_agent.py`
- [ ] Build comparison UI (movie picker + side-by-side result)
- [ ] Add `GET /api/ai/users/{id}/watchlist-priority` endpoint
- [ ] Add `prioritize_watchlist()` in `ai_agent.py`
- [ ] Add "AI Sort" button + ranked view to watchlist UI
- [ ] Add `GET /api/ai/people/{id}/career-lens` endpoint
- [ ] Add `analyze_career()` in `ai_agent.py`
- [ ] Add "Career Lens" button to person detail page

### Phase 3 — Pitch It, Hidden Gems, Vibe Card
- [ ] Add `GET /api/ai/movies/{id}/pitch` endpoint with `?tone=` param
- [ ] Add `generate_pitch()` in `ai_agent.py`
- [ ] Build pitch UI (3 tone buttons + pitch card) on movie detail page
- [ ] Add `GET /api/ai/users/{id}/hidden-gems` endpoint
- [ ] Add `find_hidden_gems()` in `ai_agent.py`
- [ ] Build hidden gems UI in AI tab
- [ ] Add `GET /api/ai/movies/{id}/vibe` endpoint
- [ ] Add `generate_vibe_card()` in `ai_agent.py`
- [ ] Build vibe card UI on movie detail page

### Phase 4 — Blind Spots, Trivia, Era, Watch Party
- [ ] Add `GET /api/ai/users/{id}/blind-spots` endpoint + `find_blind_spots()` function
- [ ] Build Cinema Diet UI (gap cards + progress bars) in AI tab
- [ ] Add `GET /api/ai/movies/{id}/trivia` endpoint + `generate_trivia()` function
- [ ] Build interactive quiz UI on movie detail page
- [ ] Add `GET /api/ai/insights/era` endpoint + `analyze_era()` function
- [ ] Build Eras section on Stats page with decade selector
- [ ] Add `POST /api/ai/watch-party` endpoint + `plan_watch_party()` function
- [ ] Build Watch Party UI (group type selector + result card) on home page

---

## File Map (what gets created/changed)

```
Modified:
  app/services/ai_agent.py       ← Ollama client + 8 new AI functions
  app/routers/ai.py              ← 9 new endpoints
  requirements.txt               ← openai replaces anthropic
  .env.example                   ← Ollama config vars
  docker-compose.yml             ← remove ANTHROPIC_API_KEY
  static/index.html              ← new UI panels
  static/js/app.js               ← new frontend functions
  static/css/style.css           ← new component styles

Created:
  app/services/chatbot.py        ← tool definitions + calling loop (chatbot only)
```

---

## Notes

- All features degrade gracefully if Ollama is not running — return a friendly error, never crash
- Use `llama3.1:8b` only for chatbot (tool use) and comparison/career (complex reasoning)
- Use `llama3.2:3b` for everything else — it's 3× faster and good enough for structured output
- Keep all prompts asking for JSON output — parse with `json.loads()`, same pattern as existing code
- Session store for chatbot is in-memory (dict) — sufficient for a hackathon, restarts clear history
