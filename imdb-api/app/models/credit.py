from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class Credit(Base):
    __tablename__ = "credits"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("people.id", ondelete="CASCADE"), nullable=False, index=True)
    movie_id = Column(Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False, index=True)
    role_type = Column(String(50), nullable=False)
    character_name = Column(String(255), nullable=True)

    person = relationship("Person", back_populates="credits")
    movie = relationship("Movie", back_populates="credits")

    __table_args__ = (
        UniqueConstraint("person_id", "movie_id", "role_type", name="uq_person_movie_role"),
    )
