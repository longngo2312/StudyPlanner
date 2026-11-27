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
    
def test_compare_returns_all_three():
    body = {"tasks": [{"id": "a", "name": "x", "duration": 2, "benefit": 5}], "capacity": 5}
    data = client.post("/compare", json=body).json()
    assert [r["algorithm"] for r in data["results"]] == ["dp", "greedy", "brute"]

def test_compare_skips_brute_when_too_many_tasks():
    tasks = [{"id": str(i), "name": "t", "duration": 1, "benefit": 1} for i in range(25)]
    data = client.post("/compare", json={"tasks": tasks, "capacity": 10}).json()
    assert "brute" in data["skipped"]
    assert len(data["results"]) == 2
    
def test_solve_returns_task_details():
    body = {"tasks": [{"id": "a", "name": "Algo HW", "duration": 2, "benefit": 5},
                      {"id": "b", "name": "Big", "duration": 9, "benefit": 50}],
            "capacity": 4, "algorithm": "dp"}
    r = client.post("/solve", json=body).json()
    assert [t["name"] for t in r["selected_tasks"]] == ["Algo HW"]
    assert [t["id"] for t in r["unselected_tasks"]] == ["b"]

def test_brute_force_rejected_over_limit():
    tasks = [{"id": str(i), "name": "t", "duration": 1, "benefit": 1} for i in range(25)]
    r = client.post("/solve", json={"tasks": tasks, "capacity": 10, "algorithm": "brute"})
    assert r.status_code == 400