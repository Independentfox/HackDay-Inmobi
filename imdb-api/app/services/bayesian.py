"""
Bayesian Weighted Average for Top Rated.
Formula: WR = (v / (v + m)) * R + (m / (v + m)) * C
  v = votes for the movie
  m = minimum votes required threshold
  R = average rating of the movie
  C = mean rating across ALL movies
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.movie import Movie

MINIMUM_VOTES = 10


def calculate_bayesian_rating(db: Session, movie_rating_count: int, movie_avg_rating: float) -> float:
    result = db.query(func.avg(Movie.average_rating)).filter(Movie.rating_count > 0).scalar()
    global_mean = float(result) if result else 5.0

    v = movie_rating_count
    m = MINIMUM_VOTES
    R = movie_avg_rating
    C = global_mean

    if v == 0:
        return 0.0

    return (v / (v + m)) * R + (m / (v + m)) * C


def get_global_mean(db: Session) -> float:
    result = db.query(func.avg(Movie.average_rating)).filter(Movie.rating_count > 0).scalar()
    return float(result) if result else 5.0
