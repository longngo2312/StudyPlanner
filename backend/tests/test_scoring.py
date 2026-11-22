#tests/test_scoring.py
#tests for the scoring layer

from datetime import date
from app.models import RawTask
from app.services.scoring import urgency, score_tasks

TODAY = date(2026, 11, 17)

def test_no_deadline_is_baseline():
    assert urgency(None, TODAY) == 1.0

def test_overdue_is_max_urgency():
    assert urgency(date(2026, 11, 10), TODAY) == 3.0

def test_tier_boundaries():
    assert urgency(date(2026, 11, 19), TODAY) == 2.5   # 2 days
    assert urgency(date(2026, 11, 20), TODAY) == 2.0   # 3 days
    assert urgency(date(2026, 11, 24), TODAY) == 2.0   # 7 days
    assert urgency(date(2026, 11, 25), TODAY) == 1.5   # 8 days
    assert urgency(date(2026, 12, 15), TODAY) == 1.0   # 28 days

def test_benefit_formula():
    t = RawTask(id="a", name="Exam prep", duration=4, priority=4,
                grade_weight=30, deadline=date(2026, 11, 20))
    assert score_tasks([t], TODAY)[0].benefit == 240.0   # 4 * 30 * 2.0

def test_urgent_task_outranks_identical_later_task():
    soon = RawTask(id="s", name="x", duration=2, priority=3, grade_weight=20, deadline=date(2026, 11, 18))
    later = RawTask(id="l", name="x", duration=2, priority=3, grade_weight=20, deadline=date(2026, 12, 30))
    scored = {t.id: t.benefit for t in score_tasks([soon, later], TODAY)}
    assert scored["s"] > scored["l"]