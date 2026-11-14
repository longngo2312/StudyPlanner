#app/routes/plan.py
#API routes for the StudyPlanner app

from fastapi import APIRouter
from app.models import SolveRequest, SolveResult
from app.services.runner import run

router = APIRouter()

@router.post("/solve", response_model=SolveResult)
def solve(req: SolveRequest):
    return run(req)