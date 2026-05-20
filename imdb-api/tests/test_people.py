"""Tests for People endpoints."""
import pytest


class TestAddPerson:
    def test_create_person(self, client):
        resp = client.post("/api/people/", json={
            "name": "Christopher Nolan",
            "birth_year": 1970,
            "bio": "British-American filmmaker."
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Christopher Nolan"
        assert data["birth_year"] == 1970
        assert data["id"] is not None

    def test_create_person_minimal(self, client):
        resp = client.post("/api/people/", json={"name": "No Bio Person"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "No Bio Person"

    def test_create_person_missing_name(self, client):
        resp = client.post("/api/people/", json={"birth_year": 1990})
        assert resp.status_code == 422

    def test_create_person_twice(self, client):
        for i in range(2):
            resp = client.post("/api/people/", json={"name": f"Actor {i}", "birth_year": 1980})
            assert resp.status_code == 201


class TestGetPerson:
    def test_get_person(self, client, sample_person):
        resp = client.get(f"/api/people/{sample_person['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == sample_person["id"]

    def test_get_person_twice(self, client, sample_person):
        for _ in range(2):
            resp = client.get(f"/api/people/{sample_person['id']}")
            assert resp.status_code == 200

    def test_get_person_not_found(self, client):
        resp = client.get("/api/people/99999")
        assert resp.status_code == 404


class TestSearchPeople:
    def test_search_by_name(self, client, sample_person):
        resp = client.get("/api/people/search?name=Test Actor")
        assert resp.status_code == 200
        data = resp.json()
        assert any(p["name"] == "Test Actor" for p in data)

    def test_search_case_insensitive(self, client, sample_person):
        resp = client.get("/api/people/search?name=test actor")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_search_all_people(self, client, sample_person):
        resp = client.get("/api/people/search")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_search_no_results(self, client):
        resp = client.get("/api/people/search?name=xyzxyzunknown999")
        assert resp.status_code == 200
        assert resp.json() == []


class TestFilmography:
    def test_filmography_empty(self, client, sample_person):
        resp = client.get(f"/api/people/{sample_person['id']}/filmography")
        assert resp.status_code == 200
        data = resp.json()
        assert data["person"]["id"] == sample_person["id"]
        assert data["filmography"] == {}

    def test_filmography_with_credits(self, client, sample_person, sample_movie):
        client.post("/api/credits/", json={
            "person_id": sample_person["id"],
            "movie_id": sample_movie["id"],
            "role_type": "director"
        })
        resp = client.get(f"/api/people/{sample_person['id']}/filmography")
        assert resp.status_code == 200
        data = resp.json()
        assert "As Director" in data["filmography"]

    def test_filmography_grouped_by_role(self, client, sample_person, sample_movie):
        m2 = client.post("/api/movies/", json={"title": "Movie 2", "release_year": 2021, "genres": ["Drama"], "certificate": "U"}).json()
        client.post("/api/credits/", json={"person_id": sample_person["id"], "movie_id": sample_movie["id"], "role_type": "director"})
        client.post("/api/credits/", json={"person_id": sample_person["id"], "movie_id": m2["id"], "role_type": "actor", "character_name": "Hero"})
        resp = client.get(f"/api/people/{sample_person['id']}/filmography")
        fg = resp.json()["filmography"]
        assert "As Director" in fg
        assert "As Actor" in fg

    def test_filmography_not_found(self, client):
        resp = client.get("/api/people/99999/filmography")
        assert resp.status_code == 404


class TestKnownFor:
    def test_known_for_empty(self, client, sample_person):
        resp = client.get(f"/api/people/{sample_person['id']}/known-for")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_known_for_returns_top_4(self, client, sample_person):
        for i in range(6):
            movie = client.post("/api/movies/", json={"title": f"Film {i}", "release_year": 2020, "genres": ["Drama"], "certificate": "U"}).json()
            client.post("/api/credits/", json={"person_id": sample_person["id"], "movie_id": movie["id"], "role_type": "actor", "character_name": "Hero"})
        resp = client.get(f"/api/people/{sample_person['id']}/known-for")
        assert resp.status_code == 200
        assert len(resp.json()) <= 4

    def test_known_for_not_found(self, client):
        resp = client.get("/api/people/99999/known-for")
        assert resp.status_code == 404


class TestSixDegrees:
    def _setup_connected_pair(self, client):
        p1 = client.post("/api/people/", json={"name": "Actor One"}).json()
        p2 = client.post("/api/people/", json={"name": "Actor Two"}).json()
        movie = client.post("/api/movies/", json={"title": "Shared Film", "release_year": 2020, "genres": ["Drama"], "certificate": "U"}).json()
        client.post("/api/credits/", json={"person_id": p1["id"], "movie_id": movie["id"], "role_type": "actor", "character_name": "A"})
        client.post("/api/credits/", json={"person_id": p2["id"], "movie_id": movie["id"], "role_type": "actor", "character_name": "B"})
        return p1, p2

    def test_same_person_zero_degrees(self, client, sample_person):
        resp = client.get(f"/api/people/six-degrees/{sample_person['id']}/{sample_person['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] is True
        assert data["degrees"] == 0

    def test_direct_connection_one_degree(self, client):
        p1, p2 = self._setup_connected_pair(client)
        resp = client.get(f"/api/people/six-degrees/{p1['id']}/{p2['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] is True
        assert data["degrees"] == 1
        assert len(data["path"]) == 2

    def test_direct_connection_twice(self, client):
        p1, p2 = self._setup_connected_pair(client)
        for _ in range(2):
            resp = client.get(f"/api/people/six-degrees/{p1['id']}/{p2['id']}")
            assert resp.json()["found"] is True

    def test_no_connection(self, client):
        p1 = client.post("/api/people/", json={"name": "Isolated A"}).json()
        p2 = client.post("/api/people/", json={"name": "Isolated B"}).json()
        resp = client.get(f"/api/people/six-degrees/{p1['id']}/{p2['id']}")
        assert resp.status_code == 200
        assert resp.json()["found"] is False

    def test_two_degrees(self, client):
        p1 = client.post("/api/people/", json={"name": "Star A"}).json()
        p2 = client.post("/api/people/", json={"name": "Star B"}).json()
        p3 = client.post("/api/people/", json={"name": "Star C"}).json()
        m1 = client.post("/api/movies/", json={"title": "Film AB", "release_year": 2020, "genres": ["Drama"], "certificate": "U"}).json()
        m2 = client.post("/api/movies/", json={"title": "Film BC", "release_year": 2021, "genres": ["Drama"], "certificate": "U"}).json()
        client.post("/api/credits/", json={"person_id": p1["id"], "movie_id": m1["id"], "role_type": "actor", "character_name": "A"})
        client.post("/api/credits/", json={"person_id": p2["id"], "movie_id": m1["id"], "role_type": "actor", "character_name": "B"})
        client.post("/api/credits/", json={"person_id": p2["id"], "movie_id": m2["id"], "role_type": "actor", "character_name": "B2"})
        client.post("/api/credits/", json={"person_id": p3["id"], "movie_id": m2["id"], "role_type": "actor", "character_name": "C"})
        resp = client.get(f"/api/people/six-degrees/{p1['id']}/{p3['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] is True
        assert data["degrees"] == 2

    def test_nonexistent_person(self, client):
        resp = client.get("/api/people/six-degrees/99999/88888")
        assert resp.status_code == 200
        assert resp.json()["found"] is False
