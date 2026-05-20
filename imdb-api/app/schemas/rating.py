from pydantic import BaseModel, ConfigDict, Field


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
