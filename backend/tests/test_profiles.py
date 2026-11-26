#tests/test_profiles.py
#tests for profile, task, and plan persistence

import pytest
from fastapi.testclient import TestClient

import app.db as db_module
from app.main import app


def login(c, username="jack", password="hunter2hunter2"):
    c.post(
        "/auth/register",
        json={"username": username, "password": password},
    )

    token = c.post(
        "/auth/login",
        json={"username": username, "password": password},
    ).json()["access_token"]

    c.headers["Authorization"] = f"Bearer {token}"
    return c


@pytest.fixture
def anon(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "test.db")

    with TestClient(app) as c:
        yield c


@pytest.fixture
def client(anon):
    return login(anon)


TASKS = [
    {
        "id": "a",
        "name": "Algo project",
        "duration": 6,
        "priority": 5,
        "grade_weight": 25,
    },
    {
        "id": "b",
        "name": "Read ch. 5",
        "duration": 2,
        "priority": 2,
        "grade_weight": 5,
    },
]


def make_profile(client, name="Engineer", capacity=8):
    return client.post(
        "/profiles",
        json={"name": name, "capacity": capacity},
    ).json()


# Profile tests

def test_create_and_list_profiles(client):
    p = make_profile(client)

    assert p["id"] == 1
    assert client.get("/profiles").json() == [p]


def test_unknown_profile_is_404(client):
    assert client.get("/profiles/99").status_code == 404

    assert client.post(
        "/profiles/99/tasks",
        json=TASKS,
    ).status_code == 404


def test_update_profile_changes_only_sent_fields(client):
    pid = make_profile(client)["id"]

    p = client.patch(
        f"/profiles/{pid}",
        json={"capacity": 12},
    ).json()

    assert p == {
        "id": pid,
        "name": "Engineer",
        "capacity": 12,
    }

    assert client.patch(
        f"/profiles/{pid}",
        json={"name": None},
    ).json()["name"] == "Engineer"


def test_delete_profile(client):
    pid = make_profile(client)["id"]

    assert client.delete(
        f"/profiles/{pid}"
    ).status_code == 204

    assert client.get(
        f"/profiles/{pid}"
    ).status_code == 404


# Task tests

def test_add_and_list_tasks(client):
    pid = make_profile(client)["id"]

    assert client.post(
        f"/profiles/{pid}/tasks",
        json=TASKS,
    ).status_code == 201

    saved = client.get(
        f"/profiles/{pid}/tasks"
    ).json()

    assert [t["id"] for t in saved] == ["a", "b"]
    assert saved[0]["completed"] is False


def test_duplicate_task_id_is_409(client):
    pid = make_profile(client)["id"]

    client.post(f"/profiles/{pid}/tasks", json=TASKS)

    assert client.post(
        f"/profiles/{pid}/tasks",
        json=TASKS[:1],
    ).status_code == 409


def test_same_task_id_allowed_in_different_profiles(client):
    p1 = make_profile(client)["id"]
    p2 = make_profile(client, "Part-timer", 4)["id"]

    assert client.post(
        f"/profiles/{p1}/tasks",
        json=TASKS[:1],
    ).status_code == 201

    assert client.post(
        f"/profiles/{p2}/tasks",
        json=TASKS[:1],
    ).status_code == 201


def test_mark_task_completed(client):
    pid = make_profile(client)["id"]

    client.post(f"/profiles/{pid}/tasks", json=TASKS)

    r = client.patch(
        f"/profiles/{pid}/tasks/a",
        json={"completed": True},
    )

    assert r.status_code == 200
    assert r.json()["completed"] is True

    saved = {
        t["id"]: t["completed"]
        for t in client.get(
            f"/profiles/{pid}/tasks"
        ).json()
    }

    assert saved == {"a": True, "b": False}


def test_update_task_fields(client):
    pid = make_profile(client)["id"]

    client.post(f"/profiles/{pid}/tasks", json=TASKS)

    r = client.patch(
        f"/profiles/{pid}/tasks/a",
        json={
            "name": "Updated project",
            "duration": 4,
        },
    )

    assert r.status_code == 200
    assert r.json()["name"] == "Updated project"
    assert r.json()["duration"] == 4
    assert r.json()["priority"] == 5


def test_update_task_with_multiple_fields(client):
    pid = make_profile(client)["id"]

    client.post(f"/profiles/{pid}/tasks", json=TASKS)

    t = client.patch(
        f"/profiles/{pid}/tasks/a",
        json={
            "completed": True,
            "deadline": "2026-12-01",
        },
    ).json()

    assert t["completed"] is True
    assert t["deadline"] == "2026-12-01"
    assert t["duration"] == 6


def test_patch_unknown_task_is_404(client):
    pid = make_profile(client)["id"]

    assert client.patch(
        f"/profiles/{pid}/tasks/zzz",
        json={"completed": True},
    ).status_code == 404


def test_update_missing_task_is_404(client):
    pid = make_profile(client)["id"]

    assert client.patch(
        f"/profiles/{pid}/tasks/nope",
        json={"name": "x"},
    ).status_code == 404


def test_delete_task(client):
    pid = make_profile(client)["id"]

    client.post(f"/profiles/{pid}/tasks", json=TASKS)

    assert client.delete(
        f"/profiles/{pid}/tasks/a"
    ).status_code == 204

    saved = client.get(
        f"/profiles/{pid}/tasks"
    ).json()

    assert [t["id"] for t in saved] == ["b"]


def test_delete_missing_task_is_404(client):
    pid = make_profile(client)["id"]

    assert client.delete(
        f"/profiles/{pid}/tasks/nope"
    ).status_code == 404


# Plan tests

def test_create_and_fetch_plan(client):
    pid = make_profile(client)["id"]

    client.post(f"/profiles/{pid}/tasks", json=TASKS)

    r = client.post(
        f"/profiles/{pid}/plans",
        json={"algorithm": "greedy"},
    )

    assert r.status_code == 201

    plan = r.json()

    assert set(plan["result"]["selected_ids"]) == {"a", "b"}

    assert client.get(
        f"/plans/{plan['id']}"
    ).json() == plan

    assert client.get(
        f"/profiles/{pid}/plans"
    ).json() == [plan]


def test_plan_respects_profile_capacity(client):
    pid = make_profile(client, capacity=6)["id"]

    client.post(f"/profiles/{pid}/tasks", json=TASKS)

    plan = client.post(
        f"/profiles/{pid}/plans",
        json={"algorithm": "greedy"},
    ).json()

    assert plan["result"]["total_time"] <= 6


def test_completed_task_excluded_from_plan(client):
    pid = make_profile(client)["id"]

    client.post(f"/profiles/{pid}/tasks", json=TASKS)

    client.patch(
        f"/profiles/{pid}/tasks/a",
        json={"completed": True},
    )

    plan = client.post(
        f"/profiles/{pid}/plans",
        json={"algorithm": "greedy"},
    ).json()

    assert plan["result"]["selected_ids"] == ["b"]


def test_completed_task_is_left_out_of_new_plan(client):
    pid = make_profile(client)["id"]

    client.post(f"/profiles/{pid}/tasks", json=TASKS)

    client.patch(
        f"/profiles/{pid}/tasks/a",
        json={"completed": True, "deadline": "2026-12-01"},
    )

    plan = client.post(
        f"/profiles/{pid}/plans",
        json={"algorithm": "dp"},
    ).json()

    assert plan["result"]["selected_ids"] == ["b"]


def test_delete_plan(client):
    pid = make_profile(client)["id"]

    client.post(f"/profiles/{pid}/tasks", json=TASKS)

    plan_id = client.post(
        f"/profiles/{pid}/plans",
        json={},
    ).json()["id"]

    assert client.delete(
        f"/plans/{plan_id}"
    ).status_code == 204

    assert client.get(
        f"/plans/{plan_id}"
    ).status_code == 404


# Rescheduling tests

def test_reschedule_uses_remaining_capacity(client):
    pid = make_profile(client, capacity=8)["id"]

    client.post(f"/profiles/{pid}/tasks", json=TASKS)

    r = client.post(
        f"/profiles/{pid}/reschedule",
        json={"time_used": 4, "algorithm": "greedy"},
    )

    assert r.status_code == 201
    assert r.json()["result"]["selected_ids"] == ["b"]
    assert r.json()["result"]["total_time"] <= 4


def test_reschedule_after_completing_a_task(client):
    pid = make_profile(client, capacity=8)["id"]

    client.post(f"/profiles/{pid}/tasks", json=TASKS)

    client.patch(
        f"/profiles/{pid}/tasks/a",
        json={"completed": True},
    )

    r = client.post(
        f"/profiles/{pid}/reschedule",
        json={"time_used": 6, "algorithm": "greedy"},
    )

    assert r.json()["result"]["selected_ids"] == ["b"]


def test_reschedule_when_time_is_gone(client):
    pid = make_profile(client, capacity=8)["id"]

    client.post(f"/profiles/{pid}/tasks", json=TASKS)

    r = client.post(
        f"/profiles/{pid}/reschedule",
        json={"time_used": 100, "algorithm": "greedy"},
    )

    assert r.json()["result"]["selected_ids"] == []
    assert r.json()["result"]["total_time"] == 0


def test_reschedule_saves_a_new_plan(client):
    pid = make_profile(client)["id"]

    client.post(f"/profiles/{pid}/tasks", json=TASKS)

    client.post(
        f"/profiles/{pid}/plans",
        json={"algorithm": "greedy"},
    )

    client.post(
        f"/profiles/{pid}/reschedule",
        json={"algorithm": "greedy"},
    )

    assert len(
        client.get(f"/profiles/{pid}/plans").json()
    ) == 2


def test_overdue_task_gets_priority_on_reschedule(client):
    pid = make_profile(client, capacity=4)["id"]

    tasks = [
        {
            "id": "x",
            "name": "Late essay",
            "duration": 4,
            "priority": 1,
            "grade_weight": 10,
            "deadline": "2026-11-20",
        },
        {
            "id": "y",
            "name": "Reading",
            "duration": 4,
            "priority": 2,
            "grade_weight": 10,
        },
    ]

    client.post(f"/profiles/{pid}/tasks", json=tasks)

    # Before the deadline: y has the higher score.
    early = client.post(
        f"/profiles/{pid}/reschedule",
        json={
            "algorithm": "greedy",
            "today": "2026-10-01",
        },
    ).json()

    assert early["result"]["selected_ids"] == ["y"]

    # After the deadline: x receives overdue priority.
    late = client.post(
        f"/profiles/{pid}/reschedule",
        json={
            "algorithm": "greedy",
            "today": "2026-11-21",
        },
    ).json()

    assert late["result"]["selected_ids"] == ["x"]


# Authentication tests

def test_routes_require_login(anon):
    assert anon.get("/profiles").status_code == 401

    anon.headers["Authorization"] = "Bearer not-a-real-token"

    assert anon.get("/profiles").status_code == 401


def test_register_login_me_logout(anon):
    assert anon.post(
        "/auth/register",
        json={
            "username": "ishani",
            "password": "longenough1",
        },
    ).status_code == 201

    assert anon.post(
        "/auth/register",
        json={
            "username": "ISHANI",
            "password": "longenough1",
        },
    ).status_code == 409

    assert anon.post(
        "/auth/login",
        json={
            "username": "ishani",
            "password": "wrongpass1",
        },
    ).status_code == 401

    login(anon, "ishani", "longenough1")

    assert anon.get("/auth/me").json()["username"] == "ishani"

    assert anon.post("/auth/logout").status_code == 204

    assert anon.get("/auth/me").status_code == 401


def test_short_password_rejected(anon):
    assert anon.post(
        "/auth/register",
        json={
            "username": "coleman",
            "password": "short",
        },
    ).status_code == 422


def test_users_cannot_see_each_others_data(client):
    pid = make_profile(client)["id"]

    client.post(f"/profiles/{pid}/tasks", json=TASKS)

    plan_id = client.post(
        f"/profiles/{pid}/plans",
        json={},
    ).json()["id"]

    login(client, "intruder", "password123")

    assert client.get("/profiles").json() == []

    assert client.get(
        f"/profiles/{pid}"
    ).status_code == 404

    assert client.get(
        f"/profiles/{pid}/tasks"
    ).status_code == 404

    assert client.patch(
        f"/profiles/{pid}",
        json={"capacity": 1},
    ).status_code == 404

    assert client.get(
        f"/plans/{plan_id}"
    ).status_code == 404

    assert client.delete(
        f"/plans/{plan_id}"
    ).status_code == 404


def test_delete_task_plan_and_profile(client):
    pid = make_profile(client)["id"]

    client.post(f"/profiles/{pid}/tasks", json=TASKS)

    assert client.delete(
        f"/profiles/{pid}/tasks/a"
    ).status_code == 204

    assert [
        t["id"]
        for t in client.get(
            f"/profiles/{pid}/tasks"
        ).json()
    ] == ["b"]

    plan_id = client.post(
        f"/profiles/{pid}/plans",
        json={},
    ).json()["id"]

    assert client.delete(
        f"/plans/{plan_id}"
    ).status_code == 204

    assert client.get(
        f"/plans/{plan_id}"
    ).status_code == 404

    assert client.delete(
        f"/profiles/{pid}"
    ).status_code == 204

    assert client.get(
        f"/profiles/{pid}"
    ).status_code == 404
