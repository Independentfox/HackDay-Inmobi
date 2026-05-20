from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class ReviewCreate(BaseModel):
    user_id: int
    movie_id: int
    rating: int = Field(..., ge=1, le=10)
    text: str = Field(..., min_length=1)


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    movie_id: int
    rating: int
    text: str
    helpful_votes: int


class HelpfulVote(BaseModel):
    review_id: int
