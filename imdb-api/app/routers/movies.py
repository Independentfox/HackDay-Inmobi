from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import Optional
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models import Movie, Credit, Person, Rating, Review, User, ReviewHelpfulVote
from app.schemas.movie import (
    MovieCreate, MovieUpdate, MovieResponse, MovieDetail,
    CreditInMovie, RatingDistribution, ReviewInMovie, TopRatedMovie, SimilarMovie
)
from app.services.bayesian import calculate_bayesian_rating, get_global_mean, MINIMUM_VOTES

router = APIRouter(prefix="/api/movies", tags=["Movies"])


@router.post("/", response_model=MovieResponse, status_code=201)
def add_movie(payload: MovieCreate, db: Session = Depends(get_db)):
    movie = Movie(**payload.model_dump())
    db.add(movie)
    db.commit()
    db.refresh(movie)
    return movie


@router.patch("/{movie_id}", response_model=MovieResponse)
def update_movie(movie_id: int, payload: MovieUpdate, db: Session = Depends(get_db)):
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(movie, field, value)
    db.commit()
    db.refresh(movie)
    return movie


@router.delete("/{movie_id}", status_code=204)
def delete_movie(movie_id: int, db: Session = Depends(get_db)):
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    db.delete(movie)
    db.commit()


@router.get("/search", response_model=list[MovieResponse])
def search_movies(
    title: Optional[str] = Query(None),
    genre: Optional[str] = Query(None),
    year_min: Optional[int] = Query(None),
    year_max: Optional[int] = Query(None),
    min_rating: Optional[float] = Query(None),
    certificate: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Movie)
    if title:
        query = query.filter(Movie.title.ilike(f"%{title}%"))
    if genre:
        query = query.filter(
            func.lower(func.array_to_string(Movie.genres, ',')).contains(genre.lower())
        )
    if year_min:
        query = query.filter(Movie.release_year >= year_min)
    if year_max:
        query = query.filter(Movie.release_year <= year_max)
    if min_rating:
        query = query.filter(Movie.average_rating >= min_rating)
    if certificate:
        query = query.filter(Movie.certificate == certificate)
    if language:
        query = query.filter(Movie.language.ilike(f"%{language}%"))
    return query.order_by(desc(Movie.average_rating)).offset(skip).limit(limit).all()


@router.get("/top-rated", response_model=list[TopRatedMovie])
def top_rated(limit: int = Query(50, ge=1, le=100), db: Session = Depends(get_db)):
    """Top movies with at least 10 ratings, sorted by Bayesian weighted average."""
    movies = db.query(Movie).filter(Movie.rating_count >= MINIMUM_VOTES).all()
    global_mean = get_global_mean(db)
    m = MINIMUM_VOTES

    results = []
    for movie in movies:
        v = movie.rating_count
        R = movie.average_rating
        C = global_mean
        bayesian = (v / (v + m)) * R + (m / (v + m)) * C
        results.append(TopRatedMovie(
            id=movie.id,
            title=movie.title,
            release_year=movie.release_year,
            average_rating=movie.average_rating,
            rating_count=movie.rating_count,
            bayesian_rating=round(bayesian, 2),
            poster_url=movie.poster_url
        ))

    results.sort(key=lambda x: x.bayesian_rating, reverse=True)
    return results[:limit]


@router.get("/trending", response_model=list[MovieResponse])
def trending(days: int = Query(7, ge=1, le=30), db: Session = Depends(get_db)):
    """Movies with the most ratings in the last N days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    trending_ids = (
        db.query(Rating.movie_id, func.count(Rating.id).label("cnt"))
        .filter(Rating.created_at >= cutoff)
        .group_by(Rating.movie_id)
        .order_by(desc("cnt"))
        .limit(20)
        .all()
    )
    movie_ids = [row[0] for row in trending_ids]
    if not movie_ids:
        return []
    movies = db.query(Movie).filter(Movie.id.in_(movie_ids)).all()
    movie_map = {m.id: m for m in movies}
    return [movie_map[mid] for mid in movie_ids if mid in movie_map]


@router.get("/{movie_id}/similar", response_model=list[SimilarMovie])
def similar_movies(movie_id: int, db: Session = Depends(get_db)):
    """Movies sharing the most genres with the given movie."""
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    if not movie.genres:
        return []

    candidates = db.query(Movie).filter(Movie.id != movie_id).all()
    scored = []
    for candidate in candidates:
        overlap = len(set(movie.genres) & set(candidate.genres or []))
        if overlap > 0:
            scored.append((overlap, candidate))

    scored.sort(key=lambda x: (-x[0], -x[1].average_rating))
    return [c for _, c in scored[:10]]


@router.get("/{movie_id}", response_model=MovieDetail)
def movie_detail(movie_id: int, user_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    credits = db.query(Credit).filter(Credit.movie_id == movie_id).all()
    cast_and_crew: dict[str, list] = {}
    for c in credits:
        person = db.query(Person).filter(Person.id == c.person_id).first()
        role_key = f"As {c.role_type.replace('_', ' ').title()}"
        entry = CreditInMovie(
            person_id=c.person_id,
            person_name=person.name if person else "Unknown",
            role_type=c.role_type,
            character_name=c.character_name
        )
        cast_and_crew.setdefault(role_key, []).append(entry)

    dist_query = (
        db.query(Rating.score, func.count(Rating.id))
        .filter(Rating.movie_id == movie_id)
        .group_by(Rating.score)
        .all()
    )
    dist_map = {score: count for score, count in dist_query}
    rating_distribution = [RatingDistribution(score=i, count=dist_map.get(i, 0)) for i in range(1, 11)]

    top_reviews_query = (
        db.query(Review, User.username)
        .join(User, Review.user_id == User.id)
        .filter(Review.movie_id == movie_id)
        .order_by(desc(Review.helpful_votes))
        .limit(5)
        .all()
    )

    review_ids = [review.id for review, _ in top_reviews_query]
    voted_ids = set()
    if user_id and review_ids:
        voted_ids = {
            row[0] for row in db.query(ReviewHelpfulVote.review_id)
            .filter(
                ReviewHelpfulVote.user_id == user_id,
                ReviewHelpfulVote.review_id.in_(review_ids)
            ).all()
        }

    top_reviews = [
        ReviewInMovie(
            id=review.id,
            user_id=review.user_id,
            username=username,
            rating=review.rating,
            text=review.text,
            helpful_votes=review.helpful_votes,
            user_voted=review.id in voted_ids
        )
        for review, username in top_reviews_query
    ]

    return MovieDetail(
        id=movie.id,
        title=movie.title,
        release_year=movie.release_year,
        genres=movie.genres,
        plot_summary=movie.plot_summary,
        runtime_minutes=movie.runtime_minutes,
        language=movie.language,
        certificate=movie.certificate,
        average_rating=movie.average_rating,
        rating_count=movie.rating_count,
        poster_url=movie.poster_url,
        cast_and_crew=cast_and_crew,
        rating_distribution=rating_distribution,
        top_reviews=top_reviews
    )
