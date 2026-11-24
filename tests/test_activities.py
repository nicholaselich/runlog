from fastapi.testclient import TestClient               
from app.main import app

client = TestClient(app)


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
