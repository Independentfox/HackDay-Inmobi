from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class RatingCreate(BaseModel):
    user_id: int
    movie_id: int
    score: int = Field(..., ge=1, le=10)


class RatingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    movie_id: int
    score: int


class UserRatingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    movie_id: int
    score: int
    movie_title: str
    movie_year: int
    movie_average_rating: float
    poster_url: Optional[str] = None
    review_text: Optional[str] = None
