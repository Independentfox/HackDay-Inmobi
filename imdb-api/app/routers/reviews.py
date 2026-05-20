from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.models import Review, Movie, User, ReviewHelpfulVote
from app.schemas.review import ReviewCreate, ReviewResponse, HelpfulVote

router = APIRouter(prefix="/api/reviews", tags=["Reviews"])


@router.post("/", response_model=ReviewResponse, status_code=200)
def write_review(payload: ReviewCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    movie = db.query(Movie).filter(Movie.id == payload.movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    current_year = datetime.now(timezone.utc).year
    if movie.release_year > current_year:
        raise HTTPException(status_code=400, detail="Cannot review a movie that has not been released yet")

    existing = db.query(Review).filter(
        Review.user_id == payload.user_id,
        Review.movie_id == payload.movie_id
    ).first()

    if existing:
        existing.rating = payload.rating
        existing.text = payload.text
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        new_review = Review(
            user_id=payload.user_id,
            movie_id=payload.movie_id,
            rating=payload.rating,
            text=payload.text
        )
        db.add(new_review)
        db.commit()
        db.refresh(new_review)
        return new_review


@router.post("/helpful", response_model=ReviewResponse)
def vote_helpful(payload: HelpfulVote, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    review = db.query(Review).filter(Review.id == payload.review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    existing = db.query(ReviewHelpfulVote).filter(
        ReviewHelpfulVote.user_id == payload.user_id,
        ReviewHelpfulVote.review_id == payload.review_id
    ).first()

    if existing:
        db.delete(existing)
        review.helpful_votes = max(0, review.helpful_votes - 1)
        user_voted = False
    else:
        db.add(ReviewHelpfulVote(user_id=payload.user_id, review_id=payload.review_id))
        review.helpful_votes += 1
        user_voted = True

    db.commit()
    db.refresh(review)

    return ReviewResponse(
        id=review.id,
        user_id=review.user_id,
        movie_id=review.movie_id,
        rating=review.rating,
        text=review.text,
        helpful_votes=review.helpful_votes,
        user_voted=user_voted
    )


@router.get("/movie/{movie_id}", response_model=list[ReviewResponse])
def get_reviews_for_movie(movie_id: int, skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return db.query(Review).filter(Review.movie_id == movie_id).offset(skip).limit(limit).all()
