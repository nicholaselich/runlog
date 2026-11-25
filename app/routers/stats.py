from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, Interval, literal
from app.schemas import WeeklyStatsOut, MonthlyStatsOut
from app.models import Activity
from app.db import get_db

from datetime import date, datetime, time, timedelta, timezone

router = APIRouter(prefix="/stats", tags=["stats"])

@router.get("/weekly", response_model=list[WeeklyStatsOut])
def weekly_stats(
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    db: Session = Depends(get_db),
):
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(status_code = 422, detail="From Date Cannot Be After To Date")
    
    min_date, max_date = db.execute(
        select(
	    func.min(Activity.start_time),
	    func.max(Activity.start_time),
	)
    ).one()
    
    start_date = date_from or (min_date.date() if min_date else None)
    end_date = date_to or (max_date.date() if max_date else None)
    
    if start_date is None or end_date is None:
        return []

    start_week = start_date - timedelta(days=start_date.weekday())
    end_week = end_date - timedelta(days=end_date.weekday())
    week_expr = func.date_trunc("week", Activity.start_time)

    stmt = select(
        week_expr.label("week_start"),
        func.count(Activity.id).label("runs"),
        func.sum(Activity.distance).label("distance_m"),
        func.sum(Activity.moving_time).label("moving_time_s")
    )

    if date_from is not None:
        stmt = stmt.where(Activity.start_time >= date_from)
    if date_to is not None:
        stmt = stmt.where(Activity.start_time < date_to + timedelta(days=1))

    activity_stats = (stmt.group_by("week_start").subquery("activity_stats"))
    
    weeks = func.generate_series(
        datetime.combine(start_week, time.min).replace(tzinfo=timezone.utc),
        datetime.combine(end_week, time.min).replace(tzinfo=timezone.utc),
	literal(timedelta(weeks=1), type_=Interval())
    ).table_valued("week_start").render_derived().alias("weeks")
 
    final_stmt = select(weeks.c.week_start,
        func.coalesce(activity_stats.c.runs, 0).label("runs"),
        func.coalesce(activity_stats.c.distance_m, 0).label("distance_m"),
        func.coalesce(activity_stats.c.moving_time_s, 0).label("moving_time_s")
    )

    final_stmt = (
        final_stmt
        .select_from(weeks)
        .outerjoin(activity_stats, weeks.c.week_start == activity_stats.c.week_start)
    )
    results = db.execute(final_stmt).mappings().all()
    
    return results

@router.get("/monthly", response_model=list[MonthlyStatsOut])
def monthly_stats(
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    db: Session = Depends(get_db),
):
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(status_code = 422, detail="From Date Cannot Be After To Date")
    
    min_date, max_date = db.execute(
        select(
	    func.min(Activity.start_time),
	    func.max(Activity.start_time),
	)
    ).one()
    
    start_date = date_from or (min_date.date() if min_date else None)
    end_date = date_to or (max_date.date() if max_date else None)
    
    if start_date is None or end_date is None:
        return []

    start_month = start_date.replace(day=1)
    end_month = end_date.replace(day=1)
    month_expr = func.date_trunc("month", Activity.start_time)

    stmt = select(
        month_expr.label("month_start"),
        func.count(Activity.id).label("runs"),
        func.sum(Activity.distance).label("distance_m"),
        func.sum(Activity.moving_time).label("moving_time_s")
    )

    if date_from is not None:
        stmt = stmt.where(Activity.start_time >= date_from)
    if date_to is not None:
        stmt = stmt.where(Activity.start_time < date_to + timedelta(days=1))

    activity_stats = (stmt.group_by("month_start").subquery("activity_stats"))
    
    months = func.generate_series(
        datetime.combine(start_month, time.min).replace(tzinfo=timezone.utc),
        datetime.combine(end_month, time.min).replace(tzinfo=timezone.utc),
	literal("1 month", type_=Interval())
    ).table_valued("month_start").render_derived().alias("months")
 
    final_stmt = select(months.c.month_start,
        func.coalesce(activity_stats.c.runs, 0).label("runs"),
        func.coalesce(activity_stats.c.distance_m, 0).label("distance_m"),
        func.coalesce(activity_stats.c.moving_time_s, 0).label("moving_time_s")
    )

    final_stmt = (
        final_stmt
        .select_from(months)
        .outerjoin(activity_stats, months.c.month_start == activity_stats.c.month_start)
    )
    results = db.execute(final_stmt).mappings().all()
    
    return results
