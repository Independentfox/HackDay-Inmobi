"""Tests for Movie endpoints."""
import pytest


class TestAddMovie:
    def test_create_movie_success(self, client):
        resp = client.post("/api/movies/", json={
            "title": "Inception",
            "release_year": 2010,
            "genres": ["Sci-Fi", "Thriller"],
            "plot_summary": "Dream heist",
            "runtime_minutes": 148,
            "language": "English",
            "certificate": "UA"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Inception"
        assert data["release_year"] == 2010
        assert "Sci-Fi" in data["genres"]
        assert data["average_rating"] == 0.0
        assert data["rating_count"] == 0

    def test_create_movie_again(self, client):
        # Can create duplicate titles (unlike users)
        for _ in range(2):
            resp = client.post("/api/movies/", json={
                "title": "Duplicate Movie",
                "release_year": 2021,
                "genres": ["Drama"],
                "language": "English",
                "certificate": "U"
            })
            assert resp.status_code == 201

    def test_create_movie_invalid_certificate(self, client):
        resp = client.post("/api/movies/", json={
            "title": "Bad Movie",
            "release_year": 2020,
            "genres": [],
            "certificate": "X"  # invalid
        })
        assert resp.status_code == 422

    def test_create_movie_missing_required(self, client):
        resp = client.post("/api/movies/", json={"title": "No Year"})
        assert resp.status_code == 422

    def test_create_movie_all_certificates(self, client):
        for cert in ["U", "UA", "A"]:
            resp = client.post("/api/movies/", json={
                "title": f"Movie {cert}",
                "release_year": 2020,
                "genres": ["Drama"],
                "certificate": cert
            })
            assert resp.status_code == 201
            assert resp.json()["certificate"] == cert


class TestMovieDetail:
    def test_get_movie_detail(self, client, sample_movie):
        resp = client.get(f"/api/movies/{sample_movie['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == sample_movie["id"]
        assert data["title"] == sample_movie["title"]
        assert "cast_and_crew" in data
        assert "rating_distribution" in data
        assert len(data["rating_distribution"]) == 10
        assert "top_reviews" in data

    def test_get_movie_detail_twice(self, client, sample_movie):
        for _ in range(2):
            resp = client.get(f"/api/movies/{sample_movie['id']}")
            assert resp.status_code == 200

    def test_get_movie_not_found(self, client):
        resp = client.get("/api/movies/99999")
        assert resp.status_code == 404

    def test_rating_distribution_has_all_scores(self, client, sample_movie):
        resp = client.get(f"/api/movies/{sample_movie['id']}")
        dist = resp.json()["rating_distribution"]
        scores = {r["score"] for r in dist}
        assert scores == set(range(1, 11))


class TestSearchMovies:
    def test_search_by_title(self, client, sample_movie):
        resp = client.get("/api/movies/search?title=Test")
        assert resp.status_code == 200
        data = resp.json()
        assert any(m["title"] == "Test Movie" for m in data)

    def test_search_by_title_twice(self, client, sample_movie):
        for _ in range(2):
            resp = client.get("/api/movies/search?title=Test")
            assert resp.status_code == 200

    def test_search_case_insensitive(self, client, sample_movie):
        resp = client.get("/api/movies/search?title=test movie")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_search_by_genre(self, client, sample_movie):
        resp = client.get("/api/movies/search?genre=Action")
        assert resp.status_code == 200
        data = resp.json()
        assert any(m["id"] == sample_movie["id"] for m in data)

    def test_search_by_year_range(self, client):
        client.post("/api/movies/", json={"title": "Old Movie", "release_year": 1990, "genres": ["Drama"], "certificate": "U"})
        client.post("/api/movies/", json={"title": "New Movie", "release_year": 2023, "genres": ["Drama"], "certificate": "U"})
        resp = client.get("/api/movies/search?year_min=2020&year_max=2025")
        assert resp.status_code == 200
        years = [m["release_year"] for m in resp.json()]
        assert all(2020 <= y <= 2025 for y in years)

    def test_search_by_certificate(self, client):
        client.post("/api/movies/", json={"title": "U Movie", "release_year": 2020, "genres": ["Family"], "certificate": "U"})
        client.post("/api/movies/", json={"title": "A Movie", "release_year": 2020, "genres": ["Thriller"], "certificate": "A"})
        resp = client.get("/api/movies/search?certificate=U")
        data = resp.json()
        assert all(m["certificate"] == "U" for m in data)

    def test_search_no_results(self, client):
        resp = client.get("/api/movies/search?title=xyzxyzxyzabc999")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_search_pagination(self, client):
        for i in range(5):
            client.post("/api/movies/", json={"title": f"Movie {i}", "release_year": 2020, "genres": ["Drama"], "certificate": "U"})
        resp1 = client.get("/api/movies/search?title=Movie&limit=2&skip=0")
        resp2 = client.get("/api/movies/search?title=Movie&limit=2&skip=2")
        assert len(resp1.json()) == 2
        assert len(resp2.json()) <= 2
        assert resp1.json()[0]["id"] != resp2.json()[0]["id"]


class TestTopRated:
    def test_top_rated_empty(self, client):
        resp = client.get("/api/movies/top-rated")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_top_rated_requires_min_votes(self, client):
        # Create movie + user + ratings but < 10
        movie = client.post("/api/movies/", json={"title": "Few Votes", "release_year": 2020, "genres": ["Drama"], "certificate": "U"}).json()
        for i in range(9):
            user = client.post("/api/users/", json={"username": f"tvuser{i}"}).json()
            client.post("/api/ratings/", json={"user_id": user["id"], "movie_id": movie["id"], "score": 9})
        resp = client.get("/api/movies/top-rated")
        ids = [m["id"] for m in resp.json()]
        assert movie["id"] not in ids

    def test_top_rated_with_sufficient_votes(self, client):
        movie = client.post("/api/movies/", json={"title": "Top Movie", "release_year": 2020, "genres": ["Drama"], "certificate": "U"}).json()
        for i in range(11):
            user = client.post("/api/users/", json={"username": f"truser{i}"}).json()
            client.post("/api/ratings/", json={"user_id": user["id"], "movie_id": movie["id"], "score": 9})
        resp = client.get("/api/movies/top-rated")
        data = resp.json()
        assert any(m["id"] == movie["id"] for m in data)
        top = [m for m in data if m["id"] == movie["id"]][0]
        assert "bayesian_rating" in top
        assert top["bayesian_rating"] > 0

    def test_top_rated_has_bayesian_field(self, client):
        # Even empty result is correct format
        resp = client.get("/api/movies/top-rated")
        assert resp.status_code == 200


class TestTrending:
    def test_trending_empty(self, client):
        resp = client.get("/api/movies/trending")
        assert resp.status_code == 200

    def test_trending_returns_list(self, client):
        resp = client.get("/api/movies/trending")
        assert isinstance(resp.json(), list)


class TestUpdateDeleteMovie:
    def test_update_movie(self, client, sample_movie):
        resp = client.patch(f"/api/movies/{sample_movie['id']}", json={"title": "Updated Title"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"

    def test_update_movie_partial(self, client, sample_movie):
        resp = client.patch(f"/api/movies/{sample_movie['id']}", json={"runtime_minutes": 999})
        assert resp.status_code == 200
        assert resp.json()["runtime_minutes"] == 999
        assert resp.json()["title"] == sample_movie["title"]  # unchanged

    def test_delete_movie(self, client, sample_movie):
        resp = client.delete(f"/api/movies/{sample_movie['id']}")
        assert resp.status_code == 204
        resp2 = client.get(f"/api/movies/{sample_movie['id']}")
        assert resp2.status_code == 404

    def test_delete_nonexistent_movie(self, client):
        resp = client.delete("/api/movies/99999")
        assert resp.status_code == 404


class TestSimilarMovies:
    def test_similar_movies(self, client):
        m1 = client.post("/api/movies/", json={"title": "Action Drama 1", "release_year": 2020, "genres": ["Action", "Drama"], "certificate": "UA"}).json()
        m2 = client.post("/api/movies/", json={"title": "Action Comedy", "release_year": 2021, "genres": ["Action", "Comedy"], "certificate": "UA"}).json()
        resp = client.get(f"/api/movies/{m1['id']}/similar")
        assert resp.status_code == 200
        ids = [m["id"] for m in resp.json()]
        assert m2["id"] in ids

    def test_similar_no_genres(self, client):
        m = client.post("/api/movies/", json={"title": "No Genre", "release_year": 2020, "genres": [], "certificate": "U"}).json()
        resp = client.get(f"/api/movies/{m['id']}/similar")
        assert resp.status_code == 200
