"""Tests for Ratings and Reviews endpoints."""
import pytest


class TestRateMovie:
    def test_rate_movie_success(self, client, sample_user, sample_movie):
        resp = client.post("/api/ratings/", json={
            "user_id": sample_user["id"],
            "movie_id": sample_movie["id"],
            "score": 8
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] == 8
        assert data["user_id"] == sample_user["id"]
        assert data["movie_id"] == sample_movie["id"]

    def test_rate_updates_movie_average(self, client, sample_user, sample_movie):
        client.post("/api/ratings/", json={
            "user_id": sample_user["id"],
            "movie_id": sample_movie["id"],
            "score": 8
        })
        movie = client.get(f"/api/movies/{sample_movie['id']}").json()
        assert movie["average_rating"] == 8.0
        assert movie["rating_count"] == 1

    def test_upsert_rating(self, client, sample_user, sample_movie):
        client.post("/api/ratings/", json={"user_id": sample_user["id"], "movie_id": sample_movie["id"], "score": 5})
        resp = client.post("/api/ratings/", json={"user_id": sample_user["id"], "movie_id": sample_movie["id"], "score": 9})
        assert resp.status_code == 200
        assert resp.json()["score"] == 9
        movie = client.get(f"/api/movies/{sample_movie['id']}").json()
        assert movie["rating_count"] == 1
        assert movie["average_rating"] == 9.0

    def test_upsert_rating_twice(self, client, sample_user, sample_movie):
        for score in [7, 8]:
            resp = client.post("/api/ratings/", json={"user_id": sample_user["id"], "movie_id": sample_movie["id"], "score": score})
            assert resp.status_code == 200
        assert resp.json()["score"] == 8

    def test_rate_invalid_score_too_high(self, client, sample_user, sample_movie):
        resp = client.post("/api/ratings/", json={"user_id": sample_user["id"], "movie_id": sample_movie["id"], "score": 11})
        assert resp.status_code == 422

    def test_rate_invalid_score_too_low(self, client, sample_user, sample_movie):
        resp = client.post("/api/ratings/", json={"user_id": sample_user["id"], "movie_id": sample_movie["id"], "score": 0})
        assert resp.status_code == 422

    def test_rate_nonexistent_user(self, client, sample_movie):
        resp = client.post("/api/ratings/", json={"user_id": 99999, "movie_id": sample_movie["id"], "score": 5})
        assert resp.status_code == 404

    def test_rate_nonexistent_movie(self, client, sample_user):
        resp = client.post("/api/ratings/", json={"user_id": sample_user["id"], "movie_id": 99999, "score": 5})
        assert resp.status_code == 404

    def test_cannot_rate_future_movie(self, client, sample_user):
        future_movie = client.post("/api/movies/", json={
            "title": "Future Film",
            "release_year": 2099,
            "genres": ["Sci-Fi"],
            "certificate": "UA"
        }).json()
        resp = client.post("/api/ratings/", json={
            "user_id": sample_user["id"],
            "movie_id": future_movie["id"],
            "score": 8
        })
        assert resp.status_code == 400

    def test_multiple_users_rating_averages_correctly(self, client, sample_movie):
        users = []
        for i in range(3):
            u = client.post("/api/users/", json={"username": f"avguser{i}"}).json()
            users.append(u)
        scores = [6, 8, 10]
        for u, s in zip(users, scores):
            client.post("/api/ratings/", json={"user_id": u["id"], "movie_id": sample_movie["id"], "score": s})
        movie = client.get(f"/api/movies/{sample_movie['id']}").json()
        assert movie["rating_count"] == 3
        expected_avg = sum(scores) / len(scores)
        assert abs(movie["average_rating"] - expected_avg) < 0.01


class TestWriteReview:
    def test_write_review(self, client, sample_user, sample_movie):
        resp = client.post("/api/reviews/", json={
            "user_id": sample_user["id"],
            "movie_id": sample_movie["id"],
            "rating": 9,
            "text": "Absolute masterpiece!"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["rating"] == 9
        assert data["text"] == "Absolute masterpiece!"
        assert data["helpful_votes"] == 0

    def test_upsert_review(self, client, sample_user, sample_movie):
        client.post("/api/reviews/", json={"user_id": sample_user["id"], "movie_id": sample_movie["id"], "rating": 7, "text": "Good"})
        resp = client.post("/api/reviews/", json={"user_id": sample_user["id"], "movie_id": sample_movie["id"], "rating": 8, "text": "Very Good"})
        assert resp.status_code == 200
        assert resp.json()["text"] == "Very Good"

    def test_upsert_review_twice(self, client, sample_user, sample_movie):
        for text in ["First", "Second"]:
            resp = client.post("/api/reviews/", json={"user_id": sample_user["id"], "movie_id": sample_movie["id"], "rating": 8, "text": text})
            assert resp.status_code == 200
        assert resp.json()["text"] == "Second"

    def test_review_appears_in_movie_detail(self, client, sample_user, sample_movie):
        client.post("/api/reviews/", json={"user_id": sample_user["id"], "movie_id": sample_movie["id"], "rating": 9, "text": "Great film"})
        detail = client.get(f"/api/movies/{sample_movie['id']}").json()
        assert len(detail["top_reviews"]) >= 1
        assert detail["top_reviews"][0]["text"] == "Great film"

    def test_review_invalid_rating(self, client, sample_user, sample_movie):
        resp = client.post("/api/reviews/", json={"user_id": sample_user["id"], "movie_id": sample_movie["id"], "rating": 11, "text": "Good"})
        assert resp.status_code == 422

    def test_review_empty_text_rejected(self, client, sample_user, sample_movie):
        resp = client.post("/api/reviews/", json={"user_id": sample_user["id"], "movie_id": sample_movie["id"], "rating": 8, "text": ""})
        assert resp.status_code == 422

    def test_cannot_review_future_movie(self, client, sample_user):
        future = client.post("/api/movies/", json={"title": "Future", "release_year": 2099, "genres": ["Sci-Fi"], "certificate": "UA"}).json()
        resp = client.post("/api/reviews/", json={"user_id": sample_user["id"], "movie_id": future["id"], "rating": 8, "text": "Great"})
        assert resp.status_code == 400


class TestHelpfulVote:
    def test_vote_helpful(self, client, sample_user, sample_movie):
        review = client.post("/api/reviews/", json={"user_id": sample_user["id"], "movie_id": sample_movie["id"], "rating": 8, "text": "Great"}).json()
        resp = client.post("/api/reviews/helpful", json={"review_id": review["id"]})
        assert resp.status_code == 200
        assert resp.json()["helpful_votes"] == 1

    def test_vote_helpful_increments(self, client, sample_user, sample_movie):
        review = client.post("/api/reviews/", json={"user_id": sample_user["id"], "movie_id": sample_movie["id"], "rating": 8, "text": "Good"}).json()
        for i in range(1, 4):
            resp = client.post("/api/reviews/helpful", json={"review_id": review["id"]})
            assert resp.json()["helpful_votes"] == i

    def test_vote_helpful_nonexistent(self, client):
        resp = client.post("/api/reviews/helpful", json={"review_id": 99999})
        assert resp.status_code == 404

    def test_top_reviews_sorted_by_helpful(self, client, sample_movie):
        u1 = client.post("/api/users/", json={"username": "rev_user1"}).json()
        u2 = client.post("/api/users/", json={"username": "rev_user2"}).json()
        r1 = client.post("/api/reviews/", json={"user_id": u1["id"], "movie_id": sample_movie["id"], "rating": 8, "text": "Good review"}).json()
        r2 = client.post("/api/reviews/", json={"user_id": u2["id"], "movie_id": sample_movie["id"], "rating": 9, "text": "Better review"}).json()
        for _ in range(5):
            client.post("/api/reviews/helpful", json={"review_id": r2["id"]})
        detail = client.get(f"/api/movies/{sample_movie['id']}").json()
        assert detail["top_reviews"][0]["id"] == r2["id"]
