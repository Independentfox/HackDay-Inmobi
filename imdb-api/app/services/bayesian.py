"""
Bayesian Weighted Average for Top Rated.
Formula: WR = (v / (v + m)) * R + (m / (v + m)) * C
  v = votes for the movie
  m = minimum votes required threshold
  R = average rating of the movie
  C = mean rating across ALL movies (global weighted mean)
"""

from sqlalchemy.orm import Session
from app.models.global_stats import GlobalStats

MINIMUM_VOTES = 10


def calculate_bayesian_rating(movie_rating_count: int, movie_avg_rating: float, global_mean: float) -> float:
    v = movie_rating_count
    m = MINIMUM_VOTES
    R = movie_avg_rating
    C = global_mean

    if v == 0:
        return 0.0

    return (v / (v + m)) * R + (m / (v + m)) * C


def get_global_mean(db: Session) -> float:
    """O(1) lookup — reads the precomputed running sum/count from global_stats row 1."""
    stats = db.get(GlobalStats, 1)
    if not stats or stats.total_rating_count == 0:
        return 5.0
    return stats.total_rating_sum / stats.total_rating_count
