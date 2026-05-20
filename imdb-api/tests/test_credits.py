"""Tests for Credits endpoints."""
import pytest


class TestAddCredit:
    def test_add_director_credit(self, client, sample_person, sample_movie):
        resp = client.post("/api/credits/", json={
            "person_id": sample_person["id"],
            "movie_id": sample_movie["id"],
            "role_type": "director"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["person_id"] == sample_person["id"]
        assert data["movie_id"] == sample_movie["id"]
        assert data["role_type"] == "director"

    def test_add_actor_credit_with_character(self, client, sample_person, sample_movie):
        resp = client.post("/api/credits/", json={
            "person_id": sample_person["id"],
            "movie_id": sample_movie["id"],
            "role_type": "actor",
            "character_name": "Hero"
        })
        assert resp.status_code == 201
        assert resp.json()["character_name"] == "Hero"

    def test_add_actor_missing_character(self, client, sample_person, sample_movie):
        resp = client.post("/api/credits/", json={
            "person_id": sample_person["id"],
            "movie_id": sample_movie["id"],
            "role_type": "actor"
            # no character_name
        })
        assert resp.status_code == 400

    def test_duplicate_credit_rejected(self, client, sample_person, sample_movie):
        client.post("/api/credits/", json={
            "person_id": sample_person["id"],
            "movie_id": sample_movie["id"],
            "role_type": "director"
        })
        resp = client.post("/api/credits/", json={
            "person_id": sample_person["id"],
            "movie_id": sample_movie["id"],
            "role_type": "director"
        })
        assert resp.status_code == 409

    def test_same_person_different_roles(self, client, sample_person, sample_movie):
        r1 = client.post("/api/credits/", json={
            "person_id": sample_person["id"],
            "movie_id": sample_movie["id"],
            "role_type": "director"
        })
        r2 = client.post("/api/credits/", json={
            "person_id": sample_person["id"],
            "movie_id": sample_movie["id"],
            "role_type": "actor",
            "character_name": "Self"
        })
        assert r1.status_code == 201
        assert r2.status_code == 201

    def test_add_credit_nonexistent_movie(self, client, sample_person):
        resp = client.post("/api/credits/", json={
            "person_id": sample_person["id"],
            "movie_id": 99999,
            "role_type": "director"
        })
        assert resp.status_code == 404

    def test_add_credit_nonexistent_person(self, client, sample_movie):
        resp = client.post("/api/credits/", json={
            "person_id": 99999,
            "movie_id": sample_movie["id"],
            "role_type": "director"
        })
        assert resp.status_code == 404

    def test_get_credits_for_movie(self, client, sample_person, sample_movie):
        client.post("/api/credits/", json={
            "person_id": sample_person["id"],
            "movie_id": sample_movie["id"],
            "role_type": "director"
        })
        resp = client.get(f"/api/credits/movie/{sample_movie['id']}")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_add_multiple_credits_same_movie(self, client, sample_movie):
        for i in range(3):
            person = client.post("/api/people/", json={"name": f"Actor {i}"}).json()
            resp = client.post("/api/credits/", json={
                "person_id": person["id"],
                "movie_id": sample_movie["id"],
                "role_type": "actor",
                "character_name": f"Character {i}"
            })
            assert resp.status_code == 201
        movie_detail = client.get(f"/api/movies/{sample_movie['id']}").json()
        assert "As Actor" in movie_detail["cast_and_crew"]
        assert len(movie_detail["cast_and_crew"]["As Actor"]) == 3
