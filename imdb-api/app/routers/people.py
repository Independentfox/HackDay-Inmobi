from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional

from app.database import get_db
from app.models import Person, Credit, Movie
from app.schemas.person import (
    PersonCreate, PersonResponse, PersonFilmography, FilmographyEntry,
    KnownForMovie, SixDegreesResponse
)
from app.services.six_degrees import find_connection

router = APIRouter(prefix="/api/people", tags=["People"])


@router.post("/", response_model=PersonResponse, status_code=201)
def add_person(payload: PersonCreate, db: Session = Depends(get_db)):
    person = Person(**payload.model_dump())
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


@router.get("/search", response_model=list[PersonResponse])
def search_people(
    name: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Person)
    if name:
        query = query.filter(Person.name.ilike(f"%{name}%"))
    return query.offset(skip).limit(limit).all()


@router.get("/six-degrees/{person_a_id}/{person_b_id}", response_model=SixDegreesResponse)
def six_degrees(person_a_id: int, person_b_id: int, db: Session = Depends(get_db)):
    result = find_connection(db, person_a_id, person_b_id)
    return SixDegreesResponse(**result)


@router.get("/{person_id}", response_model=PersonResponse)
def get_person(person_id: int, db: Session = Depends(get_db)):
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")
    return person


@router.get("/{person_id}/filmography", response_model=PersonFilmography)
def filmography(person_id: int, db: Session = Depends(get_db)):
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    credits = (
        db.query(Credit, Movie)
        .join(Movie, Credit.movie_id == Movie.id)
        .filter(Credit.person_id == person_id)
        .order_by(desc(Movie.release_year))
        .all()
    )

    filmography: dict[str, list] = {}
    for credit, movie in credits:
        role_key = f"As {credit.role_type.replace('_', ' ').title()}"
        entry = FilmographyEntry(
            movie_id=movie.id,
            movie_title=movie.title,
            release_year=movie.release_year,
            character_name=credit.character_name,
            average_rating=movie.average_rating
        )
        filmography.setdefault(role_key, []).append(entry)

    return PersonFilmography(
        person=PersonResponse.model_validate(person),
        filmography=filmography
    )


@router.get("/{person_id}/known-for", response_model=list[KnownForMovie])
def known_for(person_id: int, db: Session = Depends(get_db)):
    """Top 4 highest-rated movies for a person."""
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    credits = (
        db.query(Credit, Movie)
        .join(Movie, Credit.movie_id == Movie.id)
        .filter(Credit.person_id == person_id)
        .order_by(desc(Movie.average_rating))
        .limit(4)
        .all()
    )

    return [
        KnownForMovie(
            movie_id=movie.id,
            movie_title=movie.title,
            release_year=movie.release_year,
            average_rating=movie.average_rating,
            role_type=credit.role_type
        )
        for credit, movie in credits
    ]
