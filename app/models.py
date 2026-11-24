from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Float, SmallInteger
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class Activity(Base):
    __tablename__ = "activities"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    strava_activity_id: Mapped[int] = mapped_column(BigInteger)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    activity_type: Mapped[str]
    distance: Mapped[float]
    max_heartrate: Mapped[int | None] = mapped_column(SmallInteger)
    elapsed_time: Mapped[int]
    moving_time: Mapped[int]
    avg_heartrate: Mapped[int | None] = mapped_column(SmallInteger)
    elevation_gain: Mapped[float | None]    
    elevation_loss: Mapped[float | None] 
    calories: Mapped[int | None]
    steps: Mapped[int | None]

