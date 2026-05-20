from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Person(Base):
    __tablename__ = "people"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    birth_year = Column(Integer, nullable=True)
    bio = Column(Text, nullable=True)
    photo_url = Column(String(500), nullable=True)

    credits = relationship("Credit", back_populates="person", cascade="all, delete-orphan")
