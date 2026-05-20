from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class MovieCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    release_year: int
    genres: list[str] = Field(default_factory=list)
    plot_summary: Optional[str] = None
    runtime_minutes: Optional[int] = None
    language: str = "English"
    certificate: str = Field(default="U", pattern="^(U|UA|A)$")
    poster_url: Optional[str] = None


class MovieUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    release_year: Optional[int] = None
    genres: Optional[list[str]] = None
    plot_summary: Optional[str] = None
    runtime_minutes: Optional[int] = None
    language: Optional[str] = None
    certificate: Optional[str] = Field(None, pattern="^(U|UA|A)$")
    poster_url: Optional[str] = None


class MovieResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    release_year: int
    genres: list[str]
    plot_summary: Optional[str]
    runtime_minutes: Optional[int]
    language: str
    certificate: str
    average_rating: float
    rating_count: int
    poster_url: Optional[str]


class RatingDistribution(BaseModel):
    score: int
    count: int


class CreditInMovie(BaseModel):
    person_id: int
    person_name: str
    role_type: str
    character_name: Optional[str] = None


class ReviewInMovie(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    username: str
    rating: int
    text: str
    helpful_votes: int
    user_voted: bool = False


class MovieDetail(BaseModel):
    id: int
    title: str
    release_year: int
    genres: list[str]
    plot_summary: Optional[str]
    runtime_minutes: Optional[int]
    language: str
    certificate: str
    average_rating: float
    rating_count: int
    poster_url: Optional[str]
    cast_and_crew: dict[str, list[CreditInMovie]]
    rating_distribution: list[RatingDistribution]
    top_reviews: list[ReviewInMovie]


class TopRatedMovie(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    release_year: int
    average_rating: float
    rating_count: int
    bayesian_rating: float
    poster_url: Optional[str] = None


class SimilarMovie(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    release_year: int
    genres: list[str]
    average_rating: float
    rating_count: int
    poster_url: Optional[str] = None
