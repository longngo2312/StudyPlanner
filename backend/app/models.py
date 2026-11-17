#app\models.py
#data models for the StudyPlanner application, including Task, SolveRequest, and SolveResult
#these models are defined using Pydantic's BaseModel and include validation rules for their fields

from typing import Literal
from pydantic import BaseModel, Field

class Task(BaseModel):
    id: str
    name: str
    duration: int = Field(gt=0)       #time units (ex. 30-min blocks)
    benefit: float = Field(ge=0)      #computed from priority/deadline/grade weight
    deadline: str | None = None
    course_id: str | None = None

class SolveRequest(BaseModel):
    tasks: list[Task]
    capacity: int = Field(ge=0)
    algorithm: Literal["dp", "greedy", "brute"] = "dp"

class SolveResult(BaseModel):
    selected_ids: list[str]
    total_benefit: float
    total_time: int
    runtime_ms: float
    algorithm: str
    
class SolveResult(BaseModel):
    selected_ids: list[str]
    total_benefit: float
    total_time: int
    runtime_ms: float
    algorithm: str
    quality: float | None = None   #1.0 = matches the best result found

class CompareRequest(BaseModel):
    tasks: list[Task]
    capacity: int = Field(ge=0)

class CompareResult(BaseModel):
    results: list[SolveResult]
    skipped: dict[str, str] = {}   #algorithm + reason it was skipped
    best_benefit: float