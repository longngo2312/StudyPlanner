#tests/test_profiles.py
#tests for profile, task, and plan persistence

import pytest
from fastapi.testclient import TestClient
import app.db as db_module
from app.main import app

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "test.db")
    with TestClient(app) as c:   # the "with" runs startup, which creates the tables
        yield c

TASKS = [
    {"id": "a", "name": "Algo project", "duration": 6, "priority": 5, "grade_weight": 25},
    {"id": "b", "name": "Read ch. 5", "duration": 2, "priority": 2, "grade_weight": 5},
]

def make_profile(client, name="Engineer", capacity=8):
    return client.post("/profiles", json={"name": name, "capacity": capacity}).json()

def test_create_and_list_profiles(client):
    p = make_profile(client)
    assert p["id"] == 1
    assert client.get("/profiles").json() == [p]

def test_unknown_profile_is_404(client):
    assert client.get("/profiles/99").status_code == 404
    assert client.post("/profiles/99/tasks", json=TASKS).status_code == 404

def test_add_and_list_tasks(client):
    pid = make_profile(client)["id"]
    assert client.post(f"/profiles/{pid}/tasks", json=TASKS).status_code == 201
    saved = client.get(f"/profiles/{pid}/tasks").json()
    assert [t["id"] for t in saved] == ["a", "b"]
    assert saved[0]["completed"] is False

def test_duplicate_task_id_is_409(client):
    pid = make_profile(client)["id"]
    client.post(f"/profiles/{pid}/tasks", json=TASKS)
    assert client.post(f"/profiles/{pid}/tasks", json=TASKS[:1]).status_code == 409

def test_same_task_id_allowed_in_different_profiles(client):
    p1, p2 = make_profile(client)["id"], make_profile(client, "Part-timer", 4)["id"]
    assert client.post(f"/profiles/{p1}/tasks", json=TASKS[:1]).status_code == 201
    assert client.post(f"/profiles/{p2}/tasks", json=TASKS[:1]).status_code == 201

def test_create_and_fetch_plan(client):
    pid = make_profile(client)["id"]
    client.post(f"/profiles/{pid}/tasks", json=TASKS)
    r = client.post(f"/profiles/{pid}/plans", json={"algorithm": "greedy"})
    assert r.status_code == 201
    plan = r.json()
    assert set(plan["result"]["selected_ids"]) == {"a", "b"}   # 8 hours fits both
    assert client.get(f"/plans/{plan['id']}").json() == plan
    assert client.get(f"/profiles/{pid}/plans").json() == [plan]

def test_plan_respects_profile_capacity(client):
    pid = make_profile(client, capacity=6)["id"]
    client.post(f"/profiles/{pid}/tasks", json=TASKS)
    plan = client.post(f"/profiles/{pid}/plans", json={"algorithm": "greedy"}).json()
    assert plan["result"]["total_time"] <= 6