#app/services/scoring.py
#service to compute the benefit score of a task based on its priority, deadline, and grade weight

#formula for scoring tasks: benefit = priority × grade_weight × urgency

from datetime import date
from app.models import RawTask, Task

URGENCY_TIERS = [   #(max days until deadline, multiplier)
    (0, 3.0),    #overdue or due today
    (2, 2.5),
    (7, 2.0),
    (14, 1.5),
]

def urgency(deadline: date | None, today: date) -> float:
    if deadline is None:
        return 1.0
    days = (deadline - today).days
    for max_days, multiplier in URGENCY_TIERS:
        if days <= max_days:
            return multiplier
    return 1.0

def score_tasks(raw_tasks: list[RawTask], today: date | None = None) -> list[Task]:
    today = today or date.today()
    scored = []
    for t in raw_tasks:
        benefit = t.priority * t.grade_weight * urgency(t.deadline, today)
        scored.append(Task(
            id=t.id,
            name=t.name,
            duration=t.duration,
            benefit=round(benefit, 2),
            deadline=t.deadline.isoformat() if t.deadline else None,
            course_id=t.course_id,
        ))
    return scored