from sqlalchemy import Column, Integer, Float
from app.database import Base


class GlobalStats(Base):
    __tablename__ = "global_stats"

    id = Column(Integer, primary_key=True, default=1)  # singleton — always row 1
    total_rating_sum = Column(Float, nullable=False, default=0.0)
    total_rating_count = Column(Integer, nullable=False, default=0)
