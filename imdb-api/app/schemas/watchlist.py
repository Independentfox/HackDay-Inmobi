from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class WatchlistAdd(BaseModel):
    user_id: int
    movie_id: int


class WatchlistItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    movie_id: int
    movie_title: str
    movie_year: int
    movie_rating: float
    poster_url: Optional[str] = None
    added_at: datetime
