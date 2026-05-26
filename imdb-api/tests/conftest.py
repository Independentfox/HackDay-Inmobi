"""
Test configuration — uses a real PostgreSQL test database.
Set TEST_DATABASE_URL or falls back to DATABASE_URL with test db name.
"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/imdb").replace("/imdb", "/imdb_test")
)

from app.database import Base, get_db
from app.main import app

# Create test engine
test_engine = create_engine(TEST_DATABASE_URL, pool_size=5, max_overflow=10)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create all tables for the test session."""
    # Try to create the test database
    base_url = TEST_DATABASE_URL.rsplit("/", 1)[0]
    db_name = TEST_DATABASE_URL.rsplit("/", 1)[1]
    try:
        admin_engine = create_engine(f"{base_url}/postgres", isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as conn:
            conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
            conn.execute(text(f"CREATE DATABASE {db_name}"))
        admin_engine.dispose()
    except Exception as e:
        print(f"Note: Could not reset test DB: {e}")

    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture(autouse=True)
def clean_tables():
    """Clean all tables between tests."""
    yield
    db = TestSessionLocal()
    try:
        # Delete in reverse dependency order
        from app.models.watchlist import WatchlistItem
        from app.models.review import Review
        from app.models.rating import Rating
        from app.models.credit import Credit
        from app.models.user import User
        from app.models.movie import Movie
        from app.models.person import Person
        from app.models.global_stats import GlobalStats
        for model in [WatchlistItem, Review, Rating, Credit, User, Movie, Person]:
            db.query(model).delete()
        # Reset running totals so each test starts from a clean slate
        stats = db.get(GlobalStats, 1)
        if stats:
            stats.total_rating_sum = 0.0
            stats.total_rating_count = 0
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_movie(client):
    resp = client.post("/api/movies/", json={
        "title": "Test Movie",
        "release_year": 2020,
        "genres": ["Action", "Drama"],
        "plot_summary": "A great test movie.",
        "runtime_minutes": 120,
        "language": "English",
        "certificate": "UA"
    })
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
def sample_person(client):
    resp = client.post("/api/people/", json={
        "name": "Test Actor",
        "birth_year": 1980,
        "bio": "A great test actor."
    })
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
def sample_user(client):
    resp = client.post("/api/users/", json={"username": "testuser", "password": "testpass"})
    assert resp.status_code == 201
    return resp.json()
