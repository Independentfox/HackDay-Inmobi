from sqlalchemy import Column, Integer, String, Text, ForeignKey, UniqueConstraint, CheckConstraint, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    helpful_votes = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="reviews")
    movie = relationship("Movie", back_populates="reviews")
    helpful_vote_records = relationship("ReviewHelpfulVote", back_populates="review", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="uq_user_movie_review"),
        CheckConstraint("rating >= 1 AND rating <= 10", name="valid_review_rating"),
    )


class ReviewHelpfulVote(Base):
    __tablename__ = "review_helpful_votes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    review_id = Column(Integer, ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False)

    review = relationship("Review", back_populates="helpful_vote_records")

    __table_args__ = (
        UniqueConstraint("user_id", "review_id", name="uq_user_review_helpful"),
    )
