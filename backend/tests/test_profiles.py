#tests/test_profiles.py
#tests for profile, task, and plan persistence

import pytest
from fastapi.testclient import TestClient
import app.db as db_module
from app.main import app

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "test.db")
    with TestClient(app) as c:   #"with" runs startup, which creates the tables
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

def test_mark_task_completed(client):
    pid = make_profile(client)["id"]
    client.post(f"/profiles/{pid}/tasks", json=TASKS)
    r = client.patch(f"/profiles/{pid}/tasks/a", json={"completed": True})
    assert r.status_code == 200 and r.json()["completed"] is True
    saved = {t["id"]: t["completed"] for t in client.get(f"/profiles/{pid}/tasks").json()}
    assert saved == {"a": True, "b": False}

def test_patch_unknown_task_is_404(client):
    pid = make_profile(client)["id"]
    assert client.patch(f"/profiles/{pid}/tasks/zzz", json={"completed": True}).status_code == 404

def test_completed_task_excluded_from_plan(client):
    pid = make_profile(client)["id"]
    client.post(f"/profiles/{pid}/tasks", json=TASKS)
    client.patch(f"/profiles/{pid}/tasks/a", json={"completed": True})
    plan = client.post(f"/profiles/{pid}/plans", json={"algorithm": "greedy"}).json()
    assert plan["result"]["selected_ids"] == ["b"]

def test_reschedule_uses_remaining_capacity(client):
    pid = make_profile(client, capacity=8)["id"]
    client.post(f"/profiles/{pid}/tasks", json=TASKS)          # a = 6 units, b = 2 units
    r = client.post(f"/profiles/{pid}/reschedule", json={"time_used": 4, "algorithm": "greedy"})
    assert r.status_code == 201
    assert r.json()["result"]["selected_ids"] == ["b"]         # only 4 units left, a no longer fits
    assert r.json()["result"]["total_time"] <= 4

def test_reschedule_after_completing_a_task(client):
    pid = make_profile(client, capacity=8)["id"]
    client.post(f"/profiles/{pid}/tasks", json=TASKS)
    client.patch(f"/profiles/{pid}/tasks/a", json={"completed": True})
    r = client.post(f"/profiles/{pid}/reschedule", json={"time_used": 6, "algorithm": "greedy"})
    assert r.json()["result"]["selected_ids"] == ["b"]

def test_reschedule_when_time_is_gone(client):
    pid = make_profile(client, capacity=8)["id"]
    client.post(f"/profiles/{pid}/tasks", json=TASKS)
    r = client.post(f"/profiles/{pid}/reschedule", json={"time_used": 100, "algorithm": "greedy"})
    assert r.json()["result"]["selected_ids"] == []
    assert r.json()["result"]["total_time"] == 0

def test_reschedule_saves_a_new_plan(client):
    pid = make_profile(client)["id"]
    client.post(f"/profiles/{pid}/tasks", json=TASKS)
    client.post(f"/profiles/{pid}/plans", json={"algorithm": "greedy"})
    client.post(f"/profiles/{pid}/reschedule", json={"algorithm": "greedy"})
    assert len(client.get(f"/profiles/{pid}/plans").json()) == 2

def test_overdue_task_gets_priority_on_reschedule(client):
    pid = make_profile(client, capacity=4)["id"]
    tasks = [
        {"id": "x", "name": "Late essay", "duration": 4, "priority": 1,
         "grade_weight": 10, "deadline": "2026-11-20"},
        {"id": "y", "name": "Reading", "duration": 4, "priority": 2, "grade_weight": 10},
    ]
    client.post(f"/profiles/{pid}/tasks", json=tasks)
    
    #before the deadline: x scores 10, y scores 20, so y wins.
    early = client.post(f"/profiles/{pid}/reschedule",
                        json={"algorithm": "greedy", "today": "2026-10-01"}).json()
    assert early["result"]["selected_ids"] == ["y"]
    
    #after the deadline: x is overdue and scores 30, so x wins.
    late = client.post(f"/profiles/{pid}/reschedule",
                       json={"algorithm": "greedy", "today": "2026-11-21"}).json()
    assert late["result"]["selected_ids"] == ["x"]