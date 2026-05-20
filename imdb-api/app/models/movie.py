from sqlalchemy import Column, Integer, String, Float, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from app.database import Base


class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    release_year = Column(Integer, nullable=False)
    genres = Column(ARRAY(String), nullable=False, default=[])
    plot_summary = Column(Text, nullable=True)
    runtime_minutes = Column(Integer, nullable=True)
    language = Column(String(50), nullable=False, default="English")
    certificate = Column(String(10), nullable=False, default="U")
    poster_url = Column(String(500), nullable=True)

    # Denormalized for performance — updated on each new rating
    rating_sum = Column(Float, nullable=False, default=0.0)
    rating_count = Column(Integer, nullable=False, default=0)
    average_rating = Column(Float, nullable=False, default=0.0)

    credits = relationship("Credit", back_populates="movie", cascade="all, delete-orphan")
    ratings = relationship("Rating", back_populates="movie", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="movie", cascade="all, delete-orphan")
    watchlist_items = relationship("WatchlistItem", back_populates="movie", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("certificate IN ('U', 'UA', 'A')", name="valid_certificate"),
    )
