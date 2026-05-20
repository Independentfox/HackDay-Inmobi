from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class PersonCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    birth_year: Optional[int] = None
    bio: Optional[str] = None
    photo_url: Optional[str] = None


class PersonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    birth_year: Optional[int]
    bio: Optional[str]
    photo_url: Optional[str]


class FilmographyEntry(BaseModel):
    movie_id: int
    movie_title: str
    release_year: int
    character_name: Optional[str] = None
    average_rating: float


class PersonFilmography(BaseModel):
    person: PersonResponse
    filmography: dict[str, list[FilmographyEntry]]


class KnownForMovie(BaseModel):
    movie_id: int
    movie_title: str
    release_year: int
    average_rating: float
    role_type: str


class SixDegreesNode(BaseModel):
    person_id: int
    person_name: str
    connected_via_movie_id: Optional[int] = None
    connected_via_movie_title: Optional[str] = None


class SixDegreesResponse(BaseModel):
    found: bool
    degrees: int
    path: list[SixDegreesNode]
