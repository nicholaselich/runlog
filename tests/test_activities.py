from fastapi.testclient import TestClient               
from datetime import datetime, timezone
from sqlalchemy import delete

from app.db import SessionLocal
from app.main import app
from app.models import Activity

import pytest

client = TestClient(app)

VALID_BODY = {
    "start_time": "2026-03-05T14:00:00Z",
    "activity_type": "Run",
    "distance_m": 8046.7,
    "elapsed_time_s": 3000,
    "moving_time_s": 2900,
}


def test_get_activity_found():
    response = client.get("/v1/activities/1")
    assert response.status_code == 200                 
    body = response.json()
    assert "distance_m" in body

def test_get_activity_not_found():
    response = client.get("/v1/activities/999999")
    assert response.status_code == 404                   
    
def test_get_activity_bad_id():
    response = client.get("/v1/activities/abc")
    assert response.status_code == 422  

def test_list_activities_default():
    response = client.get("/v1/activities")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_list_activities_limit():
    response = client.get("/v1/activities?limit=3")
    assert len(response.json()) == 3

def test_list_activities_too_small():
    response = client.get("/v1/activities?limit=0")
    assert response.status_code == 422

def test_list_activities_too_big():
    response = client.get("/v1/activities?limit=105")
    assert response.status_code == 422

def test_list_activities_newest_first():
    items = client.get("/v1/activities?limit=10").json()
    times = [item["start_time"] for item in items]
    assert times == sorted(times, reverse=True)

def test_list_activities_no_shared_ids():
    response1 = client.get("/v1/activities?limit=5&offset=0").json()
    response2 = client.get("/v1/activities?limit=5&offset=5").json()
    ids1 = {res["id"] for res in response1}
    ids2 = {res["id"] for res in response2}
    assert len(ids1) == 5
    assert len(ids2) == 5
    assert ids1.isdisjoint(ids2)

def test_list_activities_negative_offset():
    response = client.get("/v1/activities?limit=5&offset=-1")
    assert response.status_code == 422

def test_list_activities_past_end_offset():
    response = client.get("/v1/activities?limit=10&offset=5000")
    assert response.status_code == 200
    assert len(response.json()) == 0

def test_min_distance_filter():
    threshold = 4828.0
    response = client.get(f"/v1/activities?limit=100&min_distance_m={threshold}")

    assert response.status_code == 200
    filtered = response.json()

    assert len(filtered) > 0
    assert all(item["distance_m"] >= threshold for item in filtered)

def test_from_date_filter():
    cutoff = "2026-01-01"
    response = client.get(f"/v1/activities?limit=100&from={cutoff}")

    assert response.status_code == 200
    filtered = response.json()

    assert len(filtered) > 0
    assert all(item["start_time"][:10] >= cutoff for item in filtered)

def test_to_date_filter_is_exclusive():
    cutoff = "2026-12-01"
    response = client.get(f"/v1/activities?limit=100&to={cutoff}")

    assert response.status_code == 200
    filtered = response.json()

    assert len(filtered) > 0
    assert all(item["start_time"][:10] < cutoff for item in filtered)

def test_filters_combined():
    cutoff = "2026-01-01"
    threshold = 4828.0

    response = client.get(
        f"/v1/activities?limit=100&from={cutoff}&min_distance_m={threshold}"
    )

    assert response.status_code == 200
    filtered = response.json()
    assert len(filtered) > 0
    assert all(item["start_time"][:10] >= cutoff for item in filtered)
    assert all(item["distance_m"] >= threshold for item in filtered)

def test_filter_no_matches():
    response = client.get("/v1/activities?from=2099-10-10")
    assert response.status_code == 200
    assert response.json() == []

def test_bad_date_returns_422():
    response = client.get("/v1/activities?from=notadate")
    assert response.status_code == 422

def test_negative_min_distance_m_returns_422():
    response = client.get("/v1/activities?min_distance_m=-5")
    assert response.status_code == 422

@pytest.fixture
def created_ids():
    """Stores ids of rows created during a test for deletion"""
    ids = []
    yield ids
    session = SessionLocal()
    try: 
        session.execute(delete(Activity).where(Activity.id.in_(ids)))
    finally:
        session.close()


def post_activity(body, created_ids):
    response = client.post("/v1/activities", json=body)
    if response.status_code == 201:
        created_ids.append(response.json()["id"])
    return response

def test_create_activity_success(created_ids): 
    response = post_activity(VALID_BODY, created_ids)
    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["distance_m"] == 8046.7
    assert body["elapsed_time_s"] == 3000
    assert body["moving_time_s"] == 2900

def test_created_activity_can_be_fetched(created_ids):
    new_id = post_activity(VALID_BODY, created_ids).json()["id"]
    response = client.get(f"/v1/activities/{new_id}")
    assert response.status_code == 200
    assert response.json()["distance_m"] == 8046.7

def test_optional_fields_default_to_null(created_ids):
    body = post_activity(VALID_BODY, created_ids).json()
    assert body["avg_heartrate"] is None
    assert body["strava_activity_id"] is None

def test_two_manual_runs_do_not_conflict(created_ids):
    first = post_activity(VALID_BODY, created_ids)
    second = post_activity(VALID_BODY, created_ids)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    
def test_duplicate_strava_id_returns_409(created_ids):
    body = {**VALID_BODY, "strava_activity_id": 999999001}
    first = post_activity(body, created_ids)
    second = post_activity(body, created_ids)
    assert first.status_code == 201
    assert second.status_code == 409

def test_timezone_offset_is_normalized_to_utc(created_ids):
    body = {**VALID_BODY, "start_time": "2026-03-05T14:00:00-08:00"}
    response = post_activity(body, created_ids)
    assert response.status_code == 201
    returned = datetime.fromisoformat(response.json()["start_time"])
    assert returned == datetime(2026, 3, 5, 22, 0, tzinfo=timezone.utc)

def test_missing_required_field_returns_422(created_ids):
    body = {key: value for key, value in VALID_BODY.items() if key != "activity_type"}
    response = post_activity(body, created_ids)
    assert response.status_code == 422

@pytest.mark.parametrize(
    "overrides",
    [
        {"distance_m": 0},                # must be greater than 0
        {"elevation_gain_m": -5},         # must be at least 0
        {"start_time": "2026-03-05T14:00:00"},      # no time zone
	{"moving_time_s": 5000},          # more than elapsed (3000)
        {"distance": 5000},		  # unknown field name
        {"strava_activity_id": 0},        # must be greater than 0
    ],
)

def test_invalid_body_returns_422(overrides, created_ids):
    body = {**VALID_BODY, **overrides}
    response = post_activity(body, created_ids)
    assert response.status_code == 422

