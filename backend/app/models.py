#app\models.py
#data models for the StudyPlanner application, including Task, SolveRequest, and SolveResult
#these models are defined using Pydantic's BaseModel and include validation rules for their fields

from typing import Literal
from pydantic import BaseModel, Field
from datetime import date
from typing import Annotated

class RawTask(BaseModel):
    id: str
    name: str
    duration: int = Field(gt=0)
    priority: int = Field(ge=1, le=5)
    grade_weight: float = Field(ge=0, le=100)
    deadline: date | None = None
    course_id: str | None = None

class PlanRequest(BaseModel):
    tasks: list[RawTask]
    capacity: int = Field(ge=0)
    algorithm: Literal["dp", "greedy", "brute"] = "dp"
    today: date | None = None   #for testing; defaults to the real date

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
    quality: float | None = None   #1.0 = matches the best result found

class CompareRequest(BaseModel):
    tasks: list[Task]
    capacity: int = Field(ge=0)

class CompareResult(BaseModel):
    results: list[SolveResult]
    skipped: dict[str, str] = {}   #algorithm + reason it was skipped
    best_benefit: float

#database classes
class ProfileCreate(BaseModel):
    name: str = Field(min_length=1)
    capacity: int = Field(ge=0)

class Profile(ProfileCreate):
    id: int

class ProfileUpdate(BaseModel):   #only the fields sent are changed
    name: str | None = Field(default=None, min_length=1)
    capacity: int | None = Field(default=None, ge=0)

class StoredTask(RawTask):
    completed: bool = False

class TaskUpdate(BaseModel):   #only the fields sent are changed
    name: str | None = None
    duration: int | None = Field(default=None, gt=0)
    priority: int | None = Field(default=None, ge=1, le=5)
    grade_weight: float | None = Field(default=None, ge=0, le=100)
    deadline: date | None = None
    course_id: str | None = None
    completed: bool | None = None

#auth
class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)

class User(BaseModel):
    id: int
    username: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class PlanCreate(BaseModel):
    algorithm: Literal["dp", "greedy", "brute"] = "dp"
    today: date | None = None   #for testing

class SavedPlan(BaseModel):
    id: int
    profile_id: int
    created_at: str
    result: SolveResult

class RescheduleRequest(BaseModel):
    time_used: int = Field(default=0, ge=0)   #units already spent or lost (done + missed blocks)
    algorithm: Literal["dp", "greedy", "brute"] = "dp"
    today: date | None = None                 #for testing
    
Count = Annotated[int, Field(ge=1, le=200)]
Cap = Annotated[int, Field(ge=0, le=5000)]

class BenchmarkRequest(BaseModel):
    task_counts: list[Count] = Field(default=[10, 15, 20, 25, 30], min_length=1, max_length=10)
    capacities: list[Cap] = Field(default=[30, 60, 90], min_length=1, max_length=10)
    repeats: int = Field(default=5, ge=1, le=20)       #runs per configuration, averaged
    brute_max_n: int = Field(default=15, ge=0, le=20)  #brute force only runs at or below n
    seed: int = 42                                     #fixed seed for reproducible results

class BenchmarkRow(BaseModel):
    n: int
    capacity: int
    algorithm: str
    avg_runtime_ms: float
    avg_benefit: float
    avg_quality: float
    repeats: int

class BenchmarkResult(BaseModel):
    rows: list[BenchmarkRow]