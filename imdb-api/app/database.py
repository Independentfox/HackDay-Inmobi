import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


def _build_database_url() -> str:
    """Prefer an explicit DATABASE_URL (local dev / docker-compose / tests)
    and otherwise compose one from the discrete env vars the K8s ConfigMap
    and Secret provide (POSTGRES_USER/PASSWORD + DB_HOST/PORT/NAME)."""
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME")
    missing = [k for k, v in {"POSTGRES_USER": user, "POSTGRES_PASSWORD": password, "DB_HOST": host, "DB_NAME": name}.items() if not v]
    if missing:
        raise RuntimeError(f"DATABASE_URL not set and missing required env vars: {', '.join(missing)}")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


DATABASE_URL = _build_database_url()

engine = create_engine(
    DATABASE_URL,
    pool_size=int(os.getenv("POOL_SIZE", "5")),
    max_overflow=int(os.getenv("POOL_MAX_OVERFLOW", "10")),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
