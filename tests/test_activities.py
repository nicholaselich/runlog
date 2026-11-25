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

# List Activities Tests

def test_get_activity_found(created_ids):
    response = post_activity(VALID_BODY, created_ids)
    assert response.status_code == 201

    activity_id = response.json()["id"]
    response = client.get(f"/v1/activities/{activity_id}")

    assert response.status_code == 200
    assert "distance_m" in response.json()

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

# LIMIT, OFFSET, FILTER Tests

def test_list_activities_limit(sample_activities):
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

def test_list_activities_no_shared_ids(sample_activities):
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

def test_min_distance_filter(sample_activities):
    threshold = 4828.0
    response = client.get(f"/v1/activities?limit=100&min_distance_m={threshold}")

    assert response.status_code == 200
    filtered = response.json()

    assert len(filtered) > 0
    assert all(item["distance_m"] >= threshold for item in filtered)

def test_from_date_filter(sample_activities):
    cutoff = "2026-01-01"
    response = client.get(f"/v1/activities?limit=100&from={cutoff}")

    assert response.status_code == 200
    filtered = response.json()

    assert len(filtered) > 0
    assert all(item["start_time"][:10] >= cutoff for item in filtered)

def test_to_date_filter_is_exclusive(sample_activities):
    cutoff = "2026-12-01"
    response = client.get(f"/v1/activities?limit=100&to={cutoff}")

    assert response.status_code == 200
    filtered = response.json()

    assert len(filtered) > 0
    assert all(item["start_time"][:10] < cutoff for item in filtered)

def test_filters_combined(sample_activities):
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

# POST Tests

@pytest.fixture
def created_ids():
    """Stores ids of rows created during a test for deletion"""
    ids = []
    yield ids
    session = SessionLocal()
    try: 
        session.execute(delete(Activity).where(Activity.id.in_(ids)))
        session.commit()
    finally:
        session.close()

@pytest.fixture
def sample_activities(created_ids):
    with SessionLocal() as session:
        activities_to_add = []

        for i in range(10):
            activity = Activity(
                start_time=datetime(2026, 1, 1 + i, tzinfo=timezone.utc),
                activity_type="Run",
                distance=5000 + (i * 1000),
                elapsed_time=3000,
                moving_time=2900,
            )
            activities_to_add.append(activity)
            session.add(activity)

        session.flush()
        created_ids.extend(activity.id for activity in activities_to_add)
        session.commit()

    return activities_to_add


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

# DELETE Tests

VALID_BODY = {
    "start_time": "2026-03-05T14:00:00Z",
    "activity_type": "Run",
    "distance_m": 8046.7,
    "elapsed_time_s": 3000,
    "moving_time_s": 2900,
}

def create_run(body, created_ids):
    """Create a run through the API and return its ID"""
    response = post_activity(body, created_ids)
    assert response.status_code == 201
    return response.json()["id"]

def test_delete_activity_success(created_ids):
    run_id = create_run(VALID_BODY, created_ids) 
    response = client.delete(f"/v1/activities/{run_id}")
    assert response.status_code == 204
    assert response.text == ""

def test_deleted_activity_gone(created_ids):
    run_id = create_run(VALID_BODY, created_ids)
    client.delete(f"/v1/activities/{run_id}")
    response = client.get(f"/v1/activities/{run_id}")
    assert response.status_code == 404

def test_delete_twice_returns_404(created_ids):
    run_id = create_run(VALID_BODY, created_ids)
    first = client.delete(f"/v1/activities/{run_id}")
    second = client.delete(f"/v1/activities/{run_id}")
    assert first.status_code == 204
    assert second.status_code == 404

def test_delete_nonexistent_returns_404():
    response = client.delete("/v1/activities/999999999")
    assert response.status_code == 404


def test_delete_bad_id_returns_422():
    response = client.delete("/v1/activities/abc")
    assert response.status_code == 422

def test_delete_only_removes_that_run(created_ids):
    keep_id = create_run(VALID_BODY, created_ids)
    remove_id = create_run(VALID_BODY, created_ids)
    client.delete(f"/v1/activities/{remove_id}")
   
    assert client.get(f"/v1/activities/{keep_id}").status_code == 200
    assert client.get(f"/v1/activities/{remove_id}").status_code == 404

    client.delete(f"/v1/activities/{keep_id}")      # clean up the kept id

# PATCH Tests

@pytest.fixture
def run_id(created_ids):
    response = post_activity(VALID_BODY, created_ids)
    assert response.status_code == 201
    return response.json()["id"]

def patch(run_id, body):
    return client.patch(f"/v1/activities/{run_id}", json=body)

def fetch(run_id):
    return client.get(f"/v1/activities/{run_id}").json()

def test_patch_single_field(run_id):
    response = patch(run_id, {"activity_type": "Trail Run"})
    assert response.status_code == 200
    assert response.json()["activity_type"] == "Trail Run"

def test_patch_leaves_other_fields_alone(run_id):
    before = fetch(run_id)
    patch(run_id, {"activity_type": "Trail Run"})
    after = fetch(run_id)
    assert after["distance_m"] == before["distance_m"]
    assert after["elapsed_time_s"] == before["elapsed_time_s"]
    assert after["start_time"] == before["start_time"]

def test_patch_renamed_field_is_saved(run_id):
    response = patch(run_id, {"distance_m": 10000})
    assert response.status_code == 200
    assert response.json()["distance_m"] == 10000
    assert fetch(run_id)["distance_m"] == 10000

def test_patch_sets_then_clears_nullable_field(run_id):
    assert patch(run_id, {"avg_heartrate": 150}).json()["avg_heartrate"] == 150
    cleared = patch(run_id, {"avg_heartrate": None})
    assert cleared.status_code == 200
    assert cleared.json()["avg_heartrate"] is None

def test_patch_empty_body_changes_nothing(run_id):
    before = fetch(run_id)
    response = patch(run_id, {})
    assert response.status_code == 200
    assert fetch(run_id) == before

def test_patch_both_times_valid_together(run_id):
    response = patch(run_id, {"elapsed_time_s": 4000, "moving_time_s": 3500})
    assert response.status_code == 200
    assert response.json()["elapsed_time_s"] == 4000
    assert response.json()["moving_time_s"] == 3500

def test_patch_null_on_required_field_returns_422(run_id):
    assert patch(run_id, {"distance_m": None}).status_code == 422

def test_patch_moving_over_stored_elapsed_returns_422(run_id):
    before = fetch(run_id)
    assert patch(run_id, {"moving_time_s": 9999}).status_code == 422
    assert fetch(run_id) == before

def test_patch_elapsed_under_stored_moving_returns_422(run_id):
    before = fetch(run_id)
    assert patch(run_id, {"elapsed_time_s": 2000}).status_code == 422
    assert fetch(run_id) == before

def test_patch_invalid_value_returns_422(run_id):
    assert patch(run_id, {"distance_m": 0}).status_code == 422

def test_patch_strava_id_not_allowed(run_id):
    assert patch(run_id, {"strava_activity_id": 5}).status_code == 422

def test_patch_nonexistent_returns_404():
    response = client.patch("/v1/activities/999999999", json={"activity_type": "Run"})
    assert response.status_code == 404

def test_patch_bad_id_returns_422():
    response = client.patch("/v1/activities/abc", json={"activity_type": "Run"})
    assert response.status_code == 422

