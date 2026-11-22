#app/routes/plan.py
#API routes for the StudyPlanner app: /plan, /score, /compare, and /solve endpoints

from fastapi import APIRouter
from app.models import SolveRequest, SolveResult, CompareRequest, CompareResult, PlanRequest, Task, RawTask
from app.services.runner import run, compare
from app.services.scoring import score_tasks

router = APIRouter()

@router.post("/plan", response_model=SolveResult)
def plan(req: PlanRequest):
    tasks = score_tasks(req.tasks, req.today)
    return run(SolveRequest(tasks=tasks, capacity=req.capacity, algorithm=req.algorithm))

@router.post("/score", response_model=list[Task])
def score(tasks: list[RawTask]):
    return score_tasks(tasks)

@router.post("/compare", response_model=CompareResult)
def compare_route(req: CompareRequest):
    return compare(req)

@router.post("/solve", response_model=SolveResult)
def solve(req: SolveRequest):
    return run(req)