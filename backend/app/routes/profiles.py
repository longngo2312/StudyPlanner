#app/routes/profiles.py
#profile, task, and saved-plan endpoints (SQLite)

#create a profile (name + time budget), add tasks to it, then generate a plan 
#generating a plan loads the profile's unfinished tasks, scores them, runs the chosen algorithm, and saves the result as JSON.

import sqlite3
from fastapi import APIRouter, HTTPException
from app.db import db
from app.models import (Profile, ProfileCreate, RawTask, StoredTask,
                        PlanCreate, SavedPlan, SolveRequest, SolveResult)
from app.services.scoring import score_tasks
from app.services.runner import run, BRUTE_LIMIT

router = APIRouter()

#helper functions
def _require_profile(conn, profile_id: int):
    row = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Profile not found")
    return row

def _load_tasks(conn, profile_id: int, include_completed: bool = True) -> list[StoredTask]:
    sql = "SELECT * FROM tasks WHERE profile_id = ?"
    if not include_completed:
        sql += " AND completed = 0"
    rows = conn.execute(sql + " ORDER BY rowid", (profile_id,)).fetchall()
    return [StoredTask(**dict(r)) for r in rows]

def _row_to_plan(row) -> SavedPlan:
    return SavedPlan(
        id=row["id"],
        profile_id=row["profile_id"],
        created_at=row["created_at"],
        result=SolveResult.model_validate_json(row["result_json"]),
    )

#profiles:
@router.post("/profiles", response_model=Profile, status_code=201)
def create_profile(p: ProfileCreate):
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO profiles (name, capacity) VALUES (?, ?)", (p.name, p.capacity))
        return Profile(id=cur.lastrowid, **p.model_dump())

@router.get("/profiles", response_model=list[Profile])
def list_profiles():
    with db() as conn:
        rows = conn.execute("SELECT * FROM profiles ORDER BY id").fetchall()
        return [Profile(**dict(r)) for r in rows]

@router.get("/profiles/{profile_id}", response_model=Profile)
def get_profile(profile_id: int):
    with db() as conn:
        return Profile(**dict(_require_profile(conn, profile_id)))

#tasks
@router.post("/profiles/{profile_id}/tasks", response_model=list[StoredTask], status_code=201)
def add_tasks(profile_id: int, tasks: list[RawTask]):
    with db() as conn:
        _require_profile(conn, profile_id)
        try:
            conn.executemany(
                """INSERT INTO tasks
                   (profile_id, id, name, duration, priority, grade_weight, deadline, course_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                [(profile_id, t.id, t.name, t.duration, t.priority, t.grade_weight,
                  t.deadline.isoformat() if t.deadline else None, t.course_id)
                 for t in tasks],
            )
        except sqlite3.IntegrityError:
            raise HTTPException(409, "A task with that id already exists for this profile")
    return [StoredTask(**t.model_dump()) for t in tasks]

@router.get("/profiles/{profile_id}/tasks", response_model=list[StoredTask])
def list_tasks(profile_id: int):
    with db() as conn:
        _require_profile(conn, profile_id)
        return _load_tasks(conn, profile_id)

#plans
@router.post("/profiles/{profile_id}/plans", response_model=SavedPlan, status_code=201)
def create_plan(profile_id: int, req: PlanCreate):
    with db() as conn:
        profile = _require_profile(conn, profile_id)
        pending = _load_tasks(conn, profile_id, include_completed=False)
        if req.algorithm == "brute" and len(pending) > BRUTE_LIMIT:
            raise HTTPException(400, f"Brute force is limited to {BRUTE_LIMIT} tasks")

        scored = score_tasks(pending, req.today)
        result = run(SolveRequest(tasks=scored, capacity=profile["capacity"],
                                  algorithm=req.algorithm))
        cur = conn.execute(
            "INSERT INTO plans (profile_id, algorithm, result_json) VALUES (?, ?, ?)",
            (profile_id, req.algorithm, result.model_dump_json()))
        row = conn.execute("SELECT * FROM plans WHERE id = ?", (cur.lastrowid,)).fetchone()
        return _row_to_plan(row)

@router.get("/profiles/{profile_id}/plans", response_model=list[SavedPlan])
def list_plans(profile_id: int):
    with db() as conn:
        _require_profile(conn, profile_id)
        rows = conn.execute(
            "SELECT * FROM plans WHERE profile_id = ? ORDER BY id DESC", (profile_id,)).fetchall()
        return [_row_to_plan(r) for r in rows]

@router.get("/plans/{plan_id}", response_model=SavedPlan)
def get_plan(plan_id: int):
    with db() as conn:
        row = conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Plan not found")
        return _row_to_plan(row)