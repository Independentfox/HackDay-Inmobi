"""Tests for Health and Stats endpoints."""
import pytest


class TestHealth:
    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "healthy"}

    def test_health_endpoint_twice(self, client):
        for _ in range(2):
            resp = client.get("/health")
            assert resp.status_code == 200

    def test_ready_endpoint(self, client):
        resp = client.get("/ready")
        assert resp.status_code in (200, 503)
        if resp.status_code == 200:
            assert resp.json()["status"] == "ready"


class TestStats:
    def test_stats_empty_db(self, client):
        resp = client.get("/api/stats/")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_movies" in data
        assert "total_people" in data
        assert "total_users" in data
        assert "total_ratings" in data
        assert "total_reviews" in data
        assert "platform_avg_rating" in data

    def test_stats_count_increments(self, client, sample_movie, sample_user):
        before = client.get("/api/stats/").json()
        client.post("/api/movies/", json={"title": "Extra Movie", "release_year": 2020, "genres": ["Drama"], "certificate": "U"})
        after = client.get("/api/stats/").json()
        assert after["total_movies"] == before["total_movies"] + 1

    def test_stats_after_rating(self, client, sample_user, sample_movie):
        before = client.get("/api/stats/").json()
        client.post("/api/ratings/", json={"user_id": sample_user["id"], "movie_id": sample_movie["id"], "score": 8})
        after = client.get("/api/stats/").json()
        assert after["total_ratings"] == before["total_ratings"] + 1

    def test_stats_twice(self, client):
        for _ in range(2):
            resp = client.get("/api/stats/")
            assert resp.status_code == 200

    def test_stats_has_no_negative_counts(self, client):
        data = client.get("/api/stats/").json()
        for key in ["total_movies", "total_people", "total_users", "total_ratings", "total_reviews"]:
            assert data[key] >= 0


class TestBayesianRating:
    def test_bayesian_lower_than_raw_for_few_votes(self, client):
        """With only MINIMUM_VOTES ratings, Bayesian should be between raw avg and global mean."""
        movie = client.post("/api/movies/", json={"title": "Test Bayesian", "release_year": 2020, "genres": ["Drama"], "certificate": "U"}).json()
        users = []
        for i in range(12):
            u = client.post("/api/users/", json={"username": f"bay_user{i}"}).json()
            users.append(u)
            client.post("/api/ratings/", json={"user_id": u["id"], "movie_id": movie["id"], "score": 10})

        top = client.get("/api/movies/top-rated").json()
        top_movie = next((m for m in top if m["id"] == movie["id"]), None)
        assert top_movie is not None
        assert 0 < top_movie["bayesian_rating"] <= 10
        # Bayesian should be <= raw average (shrunk toward mean)
        assert top_movie["bayesian_rating"] <= top_movie["average_rating"]
