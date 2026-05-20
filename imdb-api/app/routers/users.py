from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.models import Rating, Review, Movie
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.schemas.rating import UserRatingResponse
from app.schemas.review import UserReviewResponse

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.post("/", response_model=UserResponse, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    user = User(username=payload.username)
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username already exists")
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/", response_model=list[UserResponse])
def list_users(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return db.query(User).offset(skip).limit(limit).all()


@router.get("/{user_id}/ratings", response_model=list[UserRatingResponse])
def get_user_ratings(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    ratings = db.query(Rating).filter(Rating.user_id == user_id).all()
    response = []
    for rating in ratings:
        movie = db.query(Movie).filter(Movie.id == rating.movie_id).first()
        if movie:
            review = db.query(Review).filter(
                Review.user_id == user_id,
                Review.movie_id == rating.movie_id
            ).first()
            response.append(UserRatingResponse(
                id=rating.id,
                user_id=rating.user_id,
                movie_id=rating.movie_id,
                score=rating.score,
                movie_title=movie.title,
                movie_year=movie.release_year,
                movie_average_rating=movie.average_rating,
                poster_url=movie.poster_url,
                review_text=review.text if review else None
            ))
    return response


@router.get("/{user_id}/reviews", response_model=list[UserReviewResponse])
def get_user_reviews(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    reviews = db.query(Review).filter(Review.user_id == user_id).all()
    response = []
    for review in reviews:
        movie = db.query(Movie).filter(Movie.id == review.movie_id).first()
        if movie:
            response.append(UserReviewResponse(
                id=review.id,
                user_id=review.user_id,
                movie_id=review.movie_id,
                rating=review.rating,
                text=review.text,
                helpful_votes=review.helpful_votes,
                movie_title=movie.title,
                movie_year=movie.release_year,
                movie_average_rating=movie.average_rating,
                poster_url=movie.poster_url
            ))
    return response
