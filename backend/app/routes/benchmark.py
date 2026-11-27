#app/routes/benchmark.py
#endpints for benchmark and sample data

from fastapi import APIRouter
from app.models import BenchmarkRequest, BenchmarkResult, RawTask
from app.services.benchmark import run_benchmark
from app.services.datagen import PERSONAS, generate_courses, generate_tasks

router = APIRouter()

@router.post("/benchmark", response_model=BenchmarkResult)
def benchmark(req: BenchmarkRequest = BenchmarkRequest()):
    return run_benchmark(req)

@router.get("/seed/personas")
def seed_personas():
    return PERSONAS

@router.get("/seed/courses")
def seed_courses(n: int = 40, seed: int = 42):
    return generate_courses(min(max(n, 1), 200), seed)

@router.get("/seed/tasks", response_model=list[RawTask])
def seed_tasks(n: int = 20, seed: int = 42):
    return generate_tasks(min(max(n, 1), 200), seed)