#test/test_benchmark.py
#tests for data genertor and benchmark endpoint

from fastapi.testclient import TestClient
from app.main import app
from app.services.datagen import generate_courses, generate_tasks

client = TestClient(app)

def test_generator_is_reproducible():
    assert generate_tasks(10, seed=1) == generate_tasks(10, seed=1)
    assert generate_courses(5, seed=1) == generate_courses(5, seed=1)

def test_generator_differs_across_seeds():
    assert generate_tasks(10, seed=1) != generate_tasks(10, seed=2)

def test_courses_only_reference_earlier_prerequisites():
    courses = generate_courses(40)
    seen = set()
    for c in courses:
        assert set(c["prerequisites"]) <= seen
        seen.add(c["course_id"])

def test_benchmark_rows_and_quality():
    body = {"task_counts": [8, 12], "capacities": [20], "repeats": 3, "brute_max_n": 10}
    rows = client.post("/benchmark", json=body).json()["rows"]
    by_key = {(r["n"], r["algorithm"]): r for r in rows}
    assert (8, "brute") in by_key and (12, "brute") not in by_key   # brute only at n <= 10
    for r in rows:
        assert 0 <= r["avg_quality"] <= 1.0 + 1e-9
    assert all(abs(r["avg_quality"] - 1.0) < 1e-9 for r in rows if r["algorithm"] in ("dp", "brute"))

def test_benchmark_rejects_oversized_requests():
    assert client.post("/benchmark", json={"task_counts": [500]}).status_code == 422
    assert client.post("/benchmark", json={"repeats": 1000}).status_code == 422

def test_seed_endpoints():
    assert len(client.get("/seed/personas").json()) == 2
    assert len(client.get("/seed/courses?n=30").json()) == 30
    assert len(client.get("/seed/tasks?n=12").json()) == 12