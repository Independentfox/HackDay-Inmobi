from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.models import Rating, Movie, User
from app.schemas.rating import RatingCreate, RatingResponse

router = APIRouter(prefix="/api/ratings", tags=["Ratings"])


@router.post("/", response_model=RatingResponse, status_code=200)
def rate_movie(payload: RatingCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    movie = db.query(Movie).filter(Movie.id == payload.movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    current_year = datetime.now(timezone.utc).year
    if movie.release_year > current_year:
        raise HTTPException(status_code=400, detail="Cannot rate a movie that has not been released yet")

    existing = db.query(Rating).filter(
        Rating.user_id == payload.user_id,
        Rating.movie_id == payload.movie_id
    ).first()

    if existing:
        old_score = existing.score
        existing.score = payload.score
        existing.updated_at = datetime.now(timezone.utc)
        movie.rating_sum = movie.rating_sum - old_score + payload.score
        movie.average_rating = movie.rating_sum / movie.rating_count
        db.commit()
        db.refresh(existing)
        return existing
    else:
        new_rating = Rating(user_id=payload.user_id, movie_id=payload.movie_id, score=payload.score)
        db.add(new_rating)
        movie.rating_sum += payload.score
        movie.rating_count += 1
        movie.average_rating = movie.rating_sum / movie.rating_count
        db.commit()
        db.refresh(new_rating)
        return new_rating


@router.get("/movie/{movie_id}", response_model=list[RatingResponse])
def get_ratings_for_movie(movie_id: int, db: Session = Depends(get_db)):
    return db.query(Rating).filter(Rating.movie_id == movie_id).all()
