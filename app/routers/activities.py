from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db import get_db
from app.models import Activity
from app.schemas import ActivityOut, ActivityCreate

from datetime import date

router = APIRouter(prefix="/activities", tags=["activities"])

@router.get("", response_model=list[ActivityOut])
def list_activities(
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    min_distance_m: float | None = Query(None, ge=0),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Activity)
    if date_from is not None:
        stmt = stmt.where(Activity.start_time >= date_from)
    if date_to is not None:
        stmt = stmt.where(Activity.start_time < date_to)
    if min_distance_m is not None:
        stmt = stmt.where(Activity.distance >= min_distance_m)

    stmt = stmt.order_by(Activity.start_time.desc()).limit(limit).offset(offset)
    return db.scalars(stmt).all()


@router.get("/{activity_id}", response_model=ActivityOut)
def get_activity(activity_id: int, db: Session = Depends(get_db)):
    activity = db.get(Activity, activity_id)
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity

@router.post("", response_model=ActivityOut, status_code=201)
def create_activity(payload: ActivityCreate, db: Session = Depends(get_db)):
    activity = Activity(
        strava_activity_id=payload.strava_activity_id,
        start_time=payload.start_time,
        activity_type=payload.activity_type,
        distance=payload.distance_m,
        elapsed_time=payload.elapsed_time_s,
        moving_time=payload.moving_time_s,
        elevation_gain=payload.elevation_gain_m,
        elevation_loss=payload.elevation_loss_m,
        avg_heartrate=payload.avg_heartrate,
        max_heartrate=payload.max_heartrate,
        calories=payload.calories,
        steps=payload.steps,
    )

    db.add(activity)
    try: 
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Activity Already Exists")
    db.refresh(activity)
    return activity
