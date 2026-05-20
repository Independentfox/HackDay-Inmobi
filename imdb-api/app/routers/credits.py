from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models import Credit, Movie, Person
from app.schemas.credit import CreditCreate, CreditResponse

router = APIRouter(prefix="/api/credits", tags=["Credits"])


@router.post("/", response_model=CreditResponse, status_code=201)
def add_credit(payload: CreditCreate, db: Session = Depends(get_db)):
    movie = db.query(Movie).filter(Movie.id == payload.movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    person = db.query(Person).filter(Person.id == payload.person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    if payload.role_type == "actor" and not payload.character_name:
        raise HTTPException(status_code=400, detail="character_name is required for actors")

    credit = Credit(**payload.model_dump())
    try:
        db.add(credit)
        db.commit()
        db.refresh(credit)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This person already has this role in this movie")
    return credit


@router.get("/movie/{movie_id}", response_model=list[CreditResponse])
def get_credits_for_movie(movie_id: int, db: Session = Depends(get_db)):
    return db.query(Credit).filter(Credit.movie_id == movie_id).all()


@router.delete("/{credit_id}", status_code=204)
def delete_credit(credit_id: int, db: Session = Depends(get_db)):
    credit = db.query(Credit).filter(Credit.id == credit_id).first()
    if not credit:
        raise HTTPException(status_code=404, detail="Credit not found")
    db.delete(credit)
    db.commit()
