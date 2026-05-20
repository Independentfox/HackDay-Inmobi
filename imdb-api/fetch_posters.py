"""
Scrapes movie poster URLs from Wikipedia (no API key needed) and
updates the poster_url field for every movie in the database.

Strategy:
  1. Search Wikipedia for the movie title
  2. Get the list of images on that page
  3. Pick the first .jpg (almost always the infobox poster)
  4. Resolve to a real Wikimedia URL via imageinfo

Run once after seeding:
    python fetch_posters.py
"""
import os
import sys
import time

import httpx

sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal
from app.models import Movie

WIKI_API = "https://en.wikipedia.org/w/api.php"
HEADERS  = {"User-Agent": "CineDB/1.0 (hackathon; educational use)"}

# Titles that Wikipedia indexes under a non-obvious article name
WIKI_OVERRIDES: dict[str, str] = {
    "PK":    "PK (film)",
    "Don":   "Don (2006 film)",
    "Queen": "Queen (2014 film)",
    "Vikram": "Vikram (2022 film)",
    "RRR":   "RRR (film)",
}

# Generic images to skip (flags, icons, logos)
SKIP_SUFFIXES = (".svg", ".png", ".gif")
# Images whose filenames suggest they are NOT a movie poster
SKIP_KEYWORDS = (
    "flag", "clapperboard", "logo", "icon", "map", "award",
    "stadium", "palace", "fort", "temple", "church", "manor",
    "building", "imax", "aerial", "waterloo", "wondercon",
)


def _wiki_get(client: httpx.Client, params: dict) -> dict:
    for attempt in range(4):
        try:
            r = client.get(WIKI_API, params=params)
            if r.status_code == 200 and r.text.strip():
                return r.json()
            if r.status_code == 429 or not r.text.strip():
                time.sleep(5 * (attempt + 1))  # hard back-off on rate limit
                continue
        except Exception:
            pass
        time.sleep(2 ** attempt)
    return {}


def _image_url(client: httpx.Client, file_title: str) -> str | None:
    data = _wiki_get(client, {
        "action":  "query",
        "titles":  file_title,
        "prop":    "imageinfo",
        "iiprop":  "url",
        "format":  "json",
    })
    for page in data.get("query", {}).get("pages", {}).values():
        info = page.get("imageinfo", [])
        if info:
            return info[0].get("url")
    return None


def _score_image(title_lower: str, movie_title: str) -> int:
    """Higher score = more likely to be the actual movie poster."""
    score = 0
    if "poster" in title_lower:
        score += 20
    if "film" in title_lower:
        score += 5
    # Reward if movie title words appear in filename
    for word in movie_title.lower().split():
        if len(word) > 3 and word in title_lower:
            score += 8
    # Penalise obvious non-poster images
    person_signals = ("_at_", "_interview", "_premiere", "promotional", "award",
                      "event", "_2013", "_2014", "_2015", "_2016", "_2017",
                      "_2018", "_2019", "_2020", "_2021", "_2022", "_2023")
    for sig in person_signals:
        if sig in title_lower:
            score -= 10
    return score


def _poster_for_page(client: httpx.Client, page_title: str, movie_title: str = "") -> str | None:
    data = _wiki_get(client, {
        "action":    "query",
        "titles":    page_title,
        "prop":      "images",
        "imlimit":   20,
        "format":    "json",
        "redirects": 1,
    })
    candidates = []
    for page in data.get("query", {}).get("pages", {}).values():
        for img in page.get("images", []):
            t = img["title"].lower()
            if any(t.endswith(s) for s in SKIP_SUFFIXES):
                continue
            if any(kw in t for kw in SKIP_KEYWORDS):
                continue
            if not (t.endswith(".jpg") or t.endswith(".jpeg")):
                continue
            score = _score_image(t, movie_title)
            candidates.append((score, img["title"]))

    if not candidates:
        return None

    # Pick highest-scored image; must have score >= 0 to avoid garbage
    candidates.sort(key=lambda x: -x[0])
    best_score, best_title = candidates[0]
    if best_score < 0:
        return None
    return _image_url(client, best_title)


def _search_page_title(client: httpx.Client, query: str) -> str | None:
    data = _wiki_get(client, {
        "action":   "query",
        "list":     "search",
        "srsearch": query,
        "format":   "json",
        "srlimit":  1,
    })
    results = data.get("query", {}).get("search", [])
    return results[0]["title"] if results else None


def get_poster(client: httpx.Client, title: str, year: int) -> str | None:
    candidates: list[str] = []

    if title in WIKI_OVERRIDES:
        candidates.append(WIKI_OVERRIDES[title])

    candidates += [
        f"{title} ({year} film)",
        f"{title} (film)",
        title,
    ]

    for candidate in candidates:
        url = _poster_for_page(client, candidate, title)
        if url:
            return url

        found_title = _search_page_title(client, f"{candidate} film")
        if found_title:
            url = _poster_for_page(client, found_title, title)
            if url:
                return url

    return None


def main():
    db = SessionLocal()
    try:
        movies    = db.query(Movie).all()
        missing   = [m for m in movies if not m.poster_url]
        print(f"Total: {len(movies)} movies  |  Missing posters: {len(missing)}\n")

        with httpx.Client(headers=HEADERS, timeout=15) as client:
            for m in missing:
                print(f"  [{m.id:>2}] {m.title} ({m.release_year}) ...", end=" ", flush=True)
                url = get_poster(client, m.title, m.release_year)
                if url:
                    m.poster_url = url
                    db.commit()
                    print("OK")
                else:
                    print("NOT FOUND")
                time.sleep(1.5)

        found = db.query(Movie).filter(Movie.poster_url.isnot(None)).count()
        print(f"\nDone. {found}/{len(movies)} movies have posters.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
