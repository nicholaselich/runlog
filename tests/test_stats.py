from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db import SessionLocal
from app.main import app
from app.models import Activity

import pytest

client = TestClient(app)

@pytest.fixture
def created_ids():
    ids = []
    yield ids

    session = SessionLocal()
    try:
        session.execute(
            delete(Activity).where(Activity.id.in_(ids))
        )
        session.commit()
    finally:
        session.close()

# WEEKLY Tests

def test_weekly_stats_default():
    response = client.get("/v1/stats/weekly")
    assert response.status_code == 200

    results = response.json()
    assert isinstance(results, list)

    if results:
        week = results[0]
        assert "week_start" in week
        assert "runs" in week
        assert "distance_m" in week
        assert "moving_time_s" in week

def create_run(start_time, distance, moving_time, created_ids):
    body = {
        "start_time": start_time,
        "activity_type": "Run",
        "distance_m": distance,
        "elapsed_time_s": moving_time + 100,
        "moving_time_s": moving_time,
    }

    response = client.post("/v1/activities", json=body)
    assert response.status_code == 201

    created_ids.append(response.json()["id"])
    return response

def test_weekly_stats_aggregates_activities(created_ids):
    create_run("2099-04-06T10:00:00Z", 1000, 900, created_ids)
    create_run("2099-04-08T10:00:00Z", 2000, 1800, created_ids)

    response = client.get(
        "/v1/stats/weekly?from=2099-04-06&to=2099-04-11"
    )
    assert response.status_code == 200

    results = response.json()
    assert len(results) == 1

    week = results[0]
    assert week["week_start"] == "2099-04-06"
    assert week["runs"] == 2
    assert week["distance_m"] == 3000
    assert week["moving_time_s"] == 2700

def test_weekly_stats_includes_empty_weeks(created_ids):
    create_run("2199-04-01T10:00:00Z", 1000, 900, created_ids)
    create_run("2199-04-15T10:00:00Z", 2000, 1800, created_ids)

    response = client.get(
        "/v1/stats/weekly?from=2199-04-01&to=2199-04-21"
    )

    assert response.status_code == 200
    results = response.json()

    assert len(results) == 3

    assert results[0]["week_start"] == "2199-04-01"
    assert results[0]["runs"] == 1

    assert results[1]["week_start"] == "2199-04-08"
    assert results[1]["runs"] == 0
    assert results[1]["distance_m"] == 0
    assert results[1]["moving_time_s"] == 0

    assert results[2]["week_start"] == "2199-04-15"
    assert results[2]["runs"] == 1

def test_weekly_stats_invalid_date_range():
    response = client.get(
        "/v1/stats/weekly?from=2026-04-10&to=2026-04-01"
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "From Date Cannot Be After To Date"

def test_weekly_stats_no_activities():
    response = client.get("/v1/stats/weekly")

    assert response.status_code == 200
    assert response.json() == []

def test_weekly_stats_from_date_filter(created_ids):
    create_run("2199-04-01T10:00:00Z", 1000, 900, created_ids)
    create_run("2199-04-08T10:00:00Z", 2000, 1800, created_ids)
    create_run("2199-04-15T10:00:00Z", 3000, 2700, created_ids)

    response = client.get(
        "/v1/stats/weekly?from=2199-04-08"
    )

    assert response.status_code == 200
    results = response.json()

    assert len(results) == 2
    assert results[0]["week_start"] == "2199-04-08"
    assert results[0]["runs"] == 1
    assert results[0]["distance_m"] == 2000

    assert results[1]["week_start"] == "2199-04-15"
    assert results[1]["runs"] == 1
    assert results[1]["distance_m"] == 3000

def test_weekly_stats_to_date_filter(created_ids):
    create_run("2199-04-01T10:00:00Z", 1000, 900, created_ids)
    create_run("2199-04-08T10:00:00Z", 2000, 1800, created_ids)
    create_run("2199-04-15T10:00:00Z", 3000, 2700, created_ids)

    response = client.get(
        "/v1/stats/weekly?to=2199-04-08"
    )

    assert response.status_code == 200
    results = response.json()

    assert len(results) == 2

    assert results[0]["week_start"] == "2199-04-01"
    assert results[0]["runs"] == 1
    assert results[0]["distance_m"] == 1000

    assert results[1]["week_start"] == "2199-04-08"
    assert results[1]["runs"] == 1
    assert results[1]["distance_m"] == 2000

def test_weekly_stats_combined_date_filters(created_ids):
    create_run("2199-04-01T10:00:00Z", 1000, 900, created_ids)
    create_run("2199-04-08T10:00:00Z", 2000, 1800, created_ids)
    create_run("2199-04-15T10:00:00Z", 3000, 2700, created_ids)
    create_run("2199-04-22T10:00:00Z", 4000, 3600, created_ids)

    response = client.get(
        "/v1/stats/weekly?from=2199-04-08&to=2199-04-15"
    )

    assert response.status_code == 200
    results = response.json()

    assert len(results) == 2

    assert results[0]["week_start"] == "2199-04-08"
    assert results[0]["runs"] == 1
    assert results[0]["distance_m"] == 2000

    assert results[1]["week_start"] == "2199-04-15"
    assert results[1]["runs"] == 1
    assert results[1]["distance_m"] == 3000

def test_weekly_stats_to_date_includes_entire_day(created_ids):
    create_run("2199-04-08T10:00:00Z", 1000, 900, created_ids)
    create_run("2199-04-08T23:59:59Z", 2000, 1800, created_ids)
    create_run("2199-04-09T00:00:00Z", 3000, 2700, created_ids)

    response = client.get(
        "/v1/stats/weekly?from=2199-04-08&to=2199-04-08"
    )

    assert response.status_code == 200
    results = response.json()

    assert len(results) == 1
    assert results[0]["runs"] == 2
    assert results[0]["distance_m"] == 3000

def test_weekly_stats_invalid_date_format():
    response = client.get(
        "/v1/stats/weekly?from=not-a-date"
    )

    assert response.status_code == 422

def test_weekly_stats_from_date_includes_entire_day(created_ids):
    create_run("2199-04-07T23:59:59Z", 1000, 900, created_ids)
    create_run("2199-04-08T00:00:00Z", 2000, 1800, created_ids)
    create_run("2199-04-08T23:59:59Z", 3000, 2700, created_ids)

    response = client.get(
        "/v1/stats/weekly?from=2199-04-08&to=2199-04-08"
    )

    assert response.status_code == 200
    results = response.json()

    assert len(results) == 1
    assert results[0]["runs"] == 2
    assert results[0]["distance_m"] == 5000

def test_weekly_stats_no_matching_activities(created_ids):
    create_run("2199-04-01T10:00:00Z", 1000, 900, created_ids)

    response = client.get(
        "/v1/stats/weekly?from=2199-05-01&to=2199-05-14"
    )

    assert response.status_code == 200
    results = response.json()

    assert len(results) == 3
    assert results[0]["runs"] == 0
    assert results[0]["distance_m"] == 0
    assert results[1]["runs"] == 0
    assert results[1]["distance_m"] == 0

# MONTHLY Tests

def test_monthly_stats_default():
    response = client.get("/v1/stats/monthly")
    assert response.status_code == 200

    results = response.json()
    assert isinstance(results, list)

    if results:
        month = results[0]
        assert "month_start" in month
        assert "runs" in month
        assert "distance_m" in month
        assert "moving_time_s" in month


def test_monthly_stats_aggregates_activities(created_ids):
    create_run("2199-04-06T10:00:00Z", 1000, 900, created_ids)
    create_run("2199-04-15T10:00:00Z", 2000, 1800, created_ids)
    create_run("2199-05-10T10:00:00Z", 3000, 2700, created_ids)

    response = client.get(
        "/v1/stats/monthly?from=2199-04-01&to=2199-05-31"
    )

    assert response.status_code == 200
    results = response.json()

    assert len(results) == 2

    assert results[0]["month_start"] == "2199-04-01"
    assert results[0]["runs"] == 2
    assert results[0]["distance_m"] == 3000
    assert results[0]["moving_time_s"] == 2700

    assert results[1]["month_start"] == "2199-05-01"
    assert results[1]["runs"] == 1
    assert results[1]["distance_m"] == 3000
    assert results[1]["moving_time_s"] == 2700


def test_monthly_stats_includes_empty_months(created_ids):
    create_run("2199-04-06T10:00:00Z", 1000, 900, created_ids)
    create_run("2199-06-15T10:00:00Z", 2000, 1800, created_ids)

    response = client.get(
        "/v1/stats/monthly?from=2199-04-01&to=2199-06-30"
    )

    assert response.status_code == 200
    results = response.json()

    assert len(results) == 3

    assert results[0]["month_start"] == "2199-04-01"
    assert results[0]["runs"] == 1

    assert results[1]["month_start"] == "2199-05-01"
    assert results[1]["runs"] == 0
    assert results[1]["distance_m"] == 0
    assert results[1]["moving_time_s"] == 0

    assert results[2]["month_start"] == "2199-06-01"
    assert results[2]["runs"] == 1


def test_monthly_stats_invalid_date_range():
    response = client.get(
        "/v1/stats/monthly?from=2026-04-10&to=2026-04-01"
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "From Date Cannot Be After To Date"


def test_monthly_stats_no_activities():
    response = client.get("/v1/stats/monthly")

    assert response.status_code == 200
    assert response.json() == []


def test_monthly_stats_from_date_filter(created_ids):
    create_run("2199-04-01T10:00:00Z", 1000, 900, created_ids)
    create_run("2199-04-15T10:00:00Z", 2000, 1800, created_ids)
    create_run("2199-05-10T10:00:00Z", 3000, 2700, created_ids)

    response = client.get(
        "/v1/stats/monthly?from=2199-04-08"
    )

    assert response.status_code == 200
    results = response.json()

    assert len(results) == 2

    assert results[0]["month_start"] == "2199-04-01"
    assert results[0]["runs"] == 1
    assert results[0]["distance_m"] == 2000

    assert results[1]["month_start"] == "2199-05-01"
    assert results[1]["runs"] == 1
    assert results[1]["distance_m"] == 3000


def test_monthly_stats_to_date_filter(created_ids):
    create_run("2199-04-01T10:00:00Z", 1000, 900, created_ids)
    create_run("2199-04-08T10:00:00Z", 2000, 1800, created_ids)
    create_run("2199-04-15T10:00:00Z", 3000, 2700, created_ids)

    response = client.get(
        "/v1/stats/monthly?to=2199-04-08"
    )

    assert response.status_code == 200
    results = response.json()

    assert len(results) == 1
    assert results[0]["month_start"] == "2199-04-01"
    assert results[0]["runs"] == 2
    assert results[0]["distance_m"] == 3000


def test_monthly_stats_combined_date_filters(created_ids):
    create_run("2199-04-01T10:00:00Z", 1000, 900, created_ids)
    create_run("2199-04-15T10:00:00Z", 2000, 1800, created_ids)
    create_run("2199-05-10T10:00:00Z", 3000, 2700, created_ids)
    create_run("2199-05-20T10:00:00Z", 4000, 3600, created_ids)

    response = client.get(
        "/v1/stats/monthly?from=2199-04-08&to=2199-05-15"
    )

    assert response.status_code == 200
    results = response.json()

    assert len(results) == 2

    assert results[0]["month_start"] == "2199-04-01"
    assert results[0]["runs"] == 1
    assert results[0]["distance_m"] == 2000

    assert results[1]["month_start"] == "2199-05-01"
    assert results[1]["runs"] == 1
    assert results[1]["distance_m"] == 3000


def test_monthly_stats_to_date_includes_entire_day(created_ids):
    create_run("2199-04-08T10:00:00Z", 1000, 900, created_ids)
    create_run("2199-04-08T23:59:59Z", 2000, 1800, created_ids)
    create_run("2199-04-09T00:00:00Z", 3000, 2700, created_ids)

    response = client.get(
        "/v1/stats/monthly?from=2199-04-08&to=2199-04-08"
    )

    assert response.status_code == 200
    results = response.json()

    assert len(results) == 1
    assert results[0]["runs"] == 2
    assert results[0]["distance_m"] == 3000


def test_monthly_stats_invalid_date_format():
    response = client.get(
        "/v1/stats/monthly?from=not-a-date"
    )

    assert response.status_code == 422


def test_monthly_stats_from_date_includes_entire_day(created_ids):
    create_run("2199-04-07T23:59:59Z", 1000, 900, created_ids)
    create_run("2199-04-08T00:00:00Z", 2000, 1800, created_ids)
    create_run("2199-04-08T23:59:59Z", 3000, 2700, created_ids)

    response = client.get(
        "/v1/stats/monthly?from=2199-04-08&to=2199-04-08"
    )

    assert response.status_code == 200
    results = response.json()

    assert len(results) == 1
    assert results[0]["runs"] == 2
    assert results[0]["distance_m"] == 5000


def test_monthly_stats_no_matching_activities(created_ids):
    create_run("2199-04-06T10:00:00Z", 1000, 900, created_ids)

    response = client.get(
        "/v1/stats/monthly?from=2199-05-01&to=2199-06-14"
    )

    assert response.status_code == 200
    results = response.json()

    assert len(results) == 2

    assert results[0]["month_start"] == "2199-05-01"
    assert results[0]["runs"] == 0
    assert results[0]["distance_m"] == 0
    assert results[0]["moving_time_s"] == 0

    assert results[1]["month_start"] == "2199-06-01"
    assert results[1]["runs"] == 0
    assert results[1]["distance_m"] == 0
    assert results[1]["moving_time_s"] == 0
