from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models import User, Movie
from app.models.watchlist import WatchlistItem as WatchlistModel
from app.schemas.watchlist import WatchlistAdd, WatchlistItem

router = APIRouter(prefix="/api/watchlist", tags=["Watchlist"])


@router.post("/", response_model=WatchlistItem, status_code=201)
def add_to_watchlist(payload: WatchlistAdd, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    movie = db.query(Movie).filter(Movie.id == payload.movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    item = WatchlistModel(user_id=payload.user_id, movie_id=payload.movie_id)
    try:
        db.add(item)
        db.commit()
        db.refresh(item)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Movie already in watchlist")

    return WatchlistItem(
        id=item.id,
        user_id=item.user_id,
        movie_id=item.movie_id,
        movie_title=movie.title,
        movie_year=movie.release_year,
        movie_rating=movie.average_rating,
        poster_url=movie.poster_url,
        added_at=item.added_at
    )


@router.get("/{user_id}", response_model=list[WatchlistItem])
def get_watchlist(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    items = db.query(WatchlistModel).filter(WatchlistModel.user_id == user_id).all()
    result = []
    for item in items:
        movie = db.query(Movie).filter(Movie.id == item.movie_id).first()
        if movie:
            result.append(WatchlistItem(
                id=item.id,
                user_id=item.user_id,
                movie_id=item.movie_id,
                movie_title=movie.title,
                movie_year=movie.release_year,
                movie_rating=movie.average_rating,
                poster_url=movie.poster_url,
                added_at=item.added_at
            ))
    return result


@router.delete("/{user_id}/{movie_id}", status_code=204)
def remove_from_watchlist(user_id: int, movie_id: int, db: Session = Depends(get_db)):
    item = db.query(WatchlistModel).filter(
        WatchlistModel.user_id == user_id,
        WatchlistModel.movie_id == movie_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not in watchlist")
    db.delete(item)
    db.commit()
