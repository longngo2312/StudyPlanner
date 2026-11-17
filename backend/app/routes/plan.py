#app/routes/plan.py
#API routes for the StudyPlanner app

from fastapi import APIRouter
from app.models import SolveRequest, SolveResult, CompareRequest, CompareResult
from app.services.runner import run, compare

router = APIRouter()

@router.post("/compare", response_model=CompareResult)
def compare_route(req: CompareRequest):
    return compare(req)

@router.post("/solve", response_model=SolveResult)
def solve(req: SolveRequest):
    return run(req)