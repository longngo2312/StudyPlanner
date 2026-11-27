#app/services/datagen.py
#synthetic data generator to produce student personas, mock coures, and random task sets for benchmarking
#fixed seed is used for reproducible results

import random
from datetime import date, timedelta
from app.models import RawTask, Task
from app.services.scoring import score_tasks

#capacity is in 30-minute blocks: 45 hours = 90 blocks.
PERSONAS = [
    {"name": "Full-time Engineering Student", "weekly_hours": 45, "capacity": 90, "task_count": 16},
    {"name": "Part-time Working Adult", "weekly_hours": 15, "capacity": 30, "task_count": 10},
]
REFERENCE_DATE = date(2026, 11, 30)   #fixed "today" so deadlines don't drift between uses

def generate_courses(n: int = 40, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    courses: list[dict] = []
    for i in range(n):
        earlier = [c["course_id"] for c in courses]
        courses.append({
            "course_id": f"C{i + 1:03d}",
            "credit_hours": rng.choice([1, 2, 3, 4]),
            "priority_score": rng.randint(1, 5),
            "prerequisites": rng.sample(earlier, k=min(len(earlier), rng.randint(0, 2))),
        })
    return courses

def generate_tasks(n: int, seed: int = 42, today: date = REFERENCE_DATE) -> list[RawTask]:
    rng = random.Random(seed)
    tasks = []
    for i in range(n):
        has_deadline = rng.random() < 0.75
        tasks.append(RawTask(
            id=f"t{i + 1}",
            name=f"Task {i + 1}",
            duration=rng.randint(1, 8),
            priority=rng.randint(1, 5),
            grade_weight=rng.choice([5, 10, 15, 20, 25, 30, 40]),
            deadline=today + timedelta(days=rng.randint(0, 30)) if has_deadline else None,
            course_id=f"C{rng.randint(1, 40):03d}",
        ))
    return tasks

def generate_scored_tasks(n: int, seed: int = 42, today: date = REFERENCE_DATE) -> list[Task]:
    return score_tasks(generate_tasks(n, seed, today), today)