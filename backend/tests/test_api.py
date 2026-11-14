#tests/test_api.py
#tests for the planner API endpoints using FastAPI's TestClient

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    assert client.get("/health").json() == {"status": "ok"}

def test_empty_tasks():
    r = client.post("/solve", json={"tasks": [], "capacity": 10, "algorithm": "greedy"})
    assert r.status_code == 200
    assert r.json()["selected_ids"] == []

def test_zero_capacity():
    body = {"tasks": [{"id": "a", "name": "x", "duration": 2, "benefit": 5}],
            "capacity": 0, "algorithm": "greedy"}
    assert client.post("/solve", json=body).json()["total_time"] == 0

def test_never_exceeds_capacity():
    body = {"tasks": [{"id": "a", "name": "x", "duration": 9, "benefit": 5}],
            "capacity": 8, "algorithm": "greedy"}
    assert client.post("/solve", json=body).json()["selected_ids"] == []