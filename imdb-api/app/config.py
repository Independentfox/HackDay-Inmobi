import os


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/imdb")
    APP_NAME: str = "IMDB API"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"


settings = Settings()
