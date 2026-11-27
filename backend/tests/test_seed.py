#test/test_seed.py
#tests for /seed and /profiles/{id}/compare U
#uses a temporary database and a logged-in test user

import pytest
from fastapi.testclient import TestClient
import app.db as db_module
from app.main import app

CREDS = {"username": "tester", "password": "testpassword123"}

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "test.db")
    with TestClient(app) as c:
        c.post("/auth/register", json=CREDS)
        token = c.post("/auth/login", json=CREDS).json()["access_token"]
        c.headers.update({"Authorization": f"Bearer {token}"})
        yield c

def test_seed_creates_personas_with_tasks(client):
    created = client.post("/seed").json()
    assert [p["name"] for p in created] == ["Full-time Engineering Student", "Part-time Working Adult"]
    assert [p["capacity"] for p in created] == [90, 30]
    for p in created:
        assert len(client.get(f"/profiles/{p['id']}/tasks").json()) > 0

def test_seed_twice_does_not_duplicate(client):
    client.post("/seed")
    assert client.post("/seed").json() == []
    assert len(client.get("/profiles").json()) == 2

def test_seed_requires_login(client):
    assert TestClient(app).post("/seed").status_code == 401

def test_seeded_profile_can_generate_a_plan(client):
    pid = client.post("/seed").json()[0]["id"]
    plan = client.post(f"/profiles/{pid}/plans", json={"algorithm": "dp"}).json()
    assert plan["result"]["total_time"] <= 90

def _abc_profile(client):
    pid = client.post("/profiles", json={"name": "ABC", "capacity": 10}).json()["id"]
    client.post(f"/profiles/{pid}/tasks", json=[   # no deadlines, so benefit = priority * grade_weight
        {"id": "A", "name": "A", "duration": 6, "priority": 5, "grade_weight": 6},   # 30
        {"id": "B", "name": "B", "duration": 5, "priority": 4, "grade_weight": 6},   # 24
        {"id": "C", "name": "C", "duration": 5, "priority": 4, "grade_weight": 6},   # 24
    ])
    return pid

def test_compare_profile_shows_dp_beating_greedy(client):
    pid = _abc_profile(client)
    data = client.post(f"/profiles/{pid}/compare", json={}).json()
    by_algo = {r["algorithm"]: r for r in data["results"]}
    assert by_algo["dp"]["total_benefit"] == 48
    assert by_algo["brute"]["total_benefit"] == 48
    assert by_algo["greedy"]["total_benefit"] == 30
    assert by_algo["greedy"]["quality"] == pytest.approx(0.625)

def test_compare_profile_uses_remaining_time(client):
    pid = _abc_profile(client)
    data = client.post(f"/profiles/{pid}/compare", json={"time_used": 5}).json()
    assert all(r["total_time"] <= 5 for r in data["results"])

def test_compare_unknown_profile_is_404(client):
    assert client.post("/profiles/999/compare", json={}).status_code == 404