"""Tests for Users and Watchlist endpoints."""
import pytest


class TestUsers:
    def test_create_user(self, client):
        resp = client.post("/api/users/", json={"username": "newuser"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "newuser"
        assert data["id"] is not None

    def test_duplicate_username_rejected(self, client):
        client.post("/api/users/", json={"username": "duplicateuser"})
        resp = client.post("/api/users/", json={"username": "duplicateuser"})
        assert resp.status_code == 409

    def test_duplicate_username_twice(self, client):
        client.post("/api/users/", json={"username": "dupcheck"})
        for _ in range(2):
            resp = client.post("/api/users/", json={"username": "dupcheck"})
            assert resp.status_code == 409

    def test_get_user(self, client, sample_user):
        resp = client.get(f"/api/users/{sample_user['id']}")
        assert resp.status_code == 200
        assert resp.json()["username"] == "testuser"

    def test_get_user_not_found(self, client):
        resp = client.get("/api/users/99999")
        assert resp.status_code == 404

    def test_list_users(self, client, sample_user):
        resp = client.get("/api/users/")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_username_too_long(self, client):
        resp = client.post("/api/users/", json={"username": "a" * 101})
        assert resp.status_code == 422


class TestWatchlist:
    def test_add_to_watchlist(self, client, sample_user, sample_movie):
        resp = client.post("/api/watchlist/", json={
            "user_id": sample_user["id"],
            "movie_id": sample_movie["id"]
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["user_id"] == sample_user["id"]
        assert data["movie_id"] == sample_movie["id"]
        assert data["movie_title"] == sample_movie["title"]

    def test_add_duplicate_watchlist_rejected(self, client, sample_user, sample_movie):
        client.post("/api/watchlist/", json={"user_id": sample_user["id"], "movie_id": sample_movie["id"]})
        resp = client.post("/api/watchlist/", json={"user_id": sample_user["id"], "movie_id": sample_movie["id"]})
        assert resp.status_code == 409

    def test_add_duplicate_twice(self, client, sample_user, sample_movie):
        client.post("/api/watchlist/", json={"user_id": sample_user["id"], "movie_id": sample_movie["id"]})
        for _ in range(2):
            resp = client.post("/api/watchlist/", json={"user_id": sample_user["id"], "movie_id": sample_movie["id"]})
            assert resp.status_code == 409

    def test_get_watchlist(self, client, sample_user, sample_movie):
        client.post("/api/watchlist/", json={"user_id": sample_user["id"], "movie_id": sample_movie["id"]})
        resp = client.get(f"/api/watchlist/{sample_user['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["movie_id"] == sample_movie["id"]

    def test_get_watchlist_multiple_movies(self, client, sample_user):
        movies = []
        for i in range(3):
            m = client.post("/api/movies/", json={"title": f"WL Movie {i}", "release_year": 2020, "genres": ["Drama"], "certificate": "U"}).json()
            movies.append(m)
            client.post("/api/watchlist/", json={"user_id": sample_user["id"], "movie_id": m["id"]})
        resp = client.get(f"/api/watchlist/{sample_user['id']}")
        assert len(resp.json()) == 3

    def test_remove_from_watchlist(self, client, sample_user, sample_movie):
        client.post("/api/watchlist/", json={"user_id": sample_user["id"], "movie_id": sample_movie["id"]})
        resp = client.delete(f"/api/watchlist/{sample_user['id']}/{sample_movie['id']}")
        assert resp.status_code == 204
        wl = client.get(f"/api/watchlist/{sample_user['id']}").json()
        assert len(wl) == 0

    def test_remove_nonexistent_watchlist_item(self, client, sample_user, sample_movie):
        resp = client.delete(f"/api/watchlist/{sample_user['id']}/{sample_movie['id']}")
        assert resp.status_code == 404

    def test_watchlist_nonexistent_user(self, client, sample_movie):
        resp = client.post("/api/watchlist/", json={"user_id": 99999, "movie_id": sample_movie["id"]})
        assert resp.status_code == 404

    def test_watchlist_nonexistent_movie(self, client, sample_user):
        resp = client.post("/api/watchlist/", json={"user_id": sample_user["id"], "movie_id": 99999})
        assert resp.status_code == 404
