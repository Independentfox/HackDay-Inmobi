from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class CreditCreate(BaseModel):
    person_id: int
    movie_id: int
    role_type: str = Field(..., min_length=1, max_length=50)
    character_name: Optional[str] = None


class CreditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    person_id: int
    movie_id: int
    role_type: str
    character_name: Optional[str]
