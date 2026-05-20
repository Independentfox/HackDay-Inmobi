from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Movie, Person, User, Rating, Review, Credit

router = APIRouter(prefix="/api/stats", tags=["Stats"])


@router.get("/")
def platform_stats(db: Session = Depends(get_db)):
    """Platform-wide statistics."""
    total_movies = db.query(func.count(Movie.id)).scalar()
    total_people = db.query(func.count(Person.id)).scalar()
    total_users = db.query(func.count(User.id)).scalar()
    total_ratings = db.query(func.count(Rating.id)).scalar()
    total_reviews = db.query(func.count(Review.id)).scalar()
    total_credits = db.query(func.count(Credit.id)).scalar()
    avg_rating = db.query(func.avg(Movie.average_rating)).filter(Movie.rating_count > 0).scalar()
    most_rated = db.query(Movie).order_by(Movie.rating_count.desc()).first()
    highest_rated = db.query(Movie).filter(Movie.rating_count >= 5).order_by(Movie.average_rating.desc()).first()

    return {
        "total_movies": total_movies,
        "total_people": total_people,
        "total_users": total_users,
        "total_ratings": total_ratings,
        "total_reviews": total_reviews,
        "total_credits": total_credits,
        "platform_avg_rating": round(float(avg_rating), 2) if avg_rating else 0.0,
        "most_rated_movie": {"id": most_rated.id, "title": most_rated.title, "rating_count": most_rated.rating_count} if most_rated else None,
        "highest_rated_movie": {"id": highest_rated.id, "title": highest_rated.title, "average_rating": round(highest_rated.average_rating, 2)} if highest_rated else None,
    }
