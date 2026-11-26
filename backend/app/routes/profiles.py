#app/routes/profiles.py
#profile, task, and saved-plan endpoints (SQLite). every route requires a logged-in user,
#and a user only ever sees their own profiles (someone else's profile is a 404, not a 403)

#create a profile (name + time budget), add tasks to it, then generate a plan
#generating a plan loads the profile's unfinished tasks, scores them, runs the chosen algorithm, and saves the result as JSON.
#marking a task completed (PATCH) and generating a new plan re-optimizes the remaining work

import sqlite3
from fastapi import APIRouter, Depends, HTTPException, Response
from app.db import db
from app.models import (Profile, ProfileCreate, ProfileUpdate, RawTask, StoredTask, TaskUpdate,
                        PlanCreate, SavedPlan, SolveRequest, SolveResult, User)
from app.routes.auth import current_user
from app.services.scoring import score_tasks
from app.services.runner import run, BRUTE_LIMIT

router = APIRouter(dependencies=[Depends(current_user)])

#helper functions
def _require_profile(conn, profile_id: int, user: User):
    row = conn.execute("SELECT * FROM profiles WHERE id = ? AND user_id = ?",
                       (profile_id, user.id)).fetchone()
    if row is None:
        raise HTTPException(404, "Profile not found")
    return row

def _to_profile(row) -> Profile:
    return Profile(id=row["id"], name=row["name"], capacity=row["capacity"])

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

def _update(conn, table: str, changes: dict, where: str, params: tuple) -> None:
    """UPDATE only the fields the client sent. Column names come from our Pydantic models, never from raw input."""
    #explicit null only clears optional columns; for required ones it is ignored
    changes = {k: v for k, v in changes.items() if v is not None or k in ("deadline", "course_id")}
    if not changes:
        return
    if changes.get("deadline") is not None:
        changes["deadline"] = changes["deadline"].isoformat()
    sets = ", ".join(f"{col} = ?" for col in changes)
    conn.execute(f"UPDATE {table} SET {sets} WHERE {where}", (*changes.values(), *params))

#profiles
@router.post("/profiles", response_model=Profile, status_code=201)
def create_profile(p: ProfileCreate, user: User = Depends(current_user)):
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO profiles (user_id, name, capacity) VALUES (?, ?, ?)",
            (user.id, p.name, p.capacity))
        return Profile(id=cur.lastrowid, **p.model_dump())

@router.get("/profiles", response_model=list[Profile])
def list_profiles(user: User = Depends(current_user)):
    with db() as conn:
        rows = conn.execute("SELECT * FROM profiles WHERE user_id = ? ORDER BY id", (user.id,)).fetchall()
        return [_to_profile(r) for r in rows]

@router.get("/profiles/{profile_id}", response_model=Profile)
def get_profile(profile_id: int, user: User = Depends(current_user)):
    with db() as conn:
        return _to_profile(_require_profile(conn, profile_id, user))

@router.patch("/profiles/{profile_id}", response_model=Profile)
def update_profile(profile_id: int, p: ProfileUpdate, user: User = Depends(current_user)):
    with db() as conn:
        _require_profile(conn, profile_id, user)
        _update(conn, "profiles", p.model_dump(exclude_unset=True), "id = ?", (profile_id,))
        return _to_profile(_require_profile(conn, profile_id, user))

@router.delete("/profiles/{profile_id}", status_code=204)
def delete_profile(profile_id: int, user: User = Depends(current_user)):
    with db() as conn:
        _require_profile(conn, profile_id, user)
        conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))   #tasks + plans cascade
    return Response(status_code=204)

#tasks
@router.post("/profiles/{profile_id}/tasks", response_model=list[StoredTask], status_code=201)
def add_tasks(profile_id: int, tasks: list[RawTask], user: User = Depends(current_user)):
    with db() as conn:
        _require_profile(conn, profile_id, user)
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
def list_tasks(profile_id: int, user: User = Depends(current_user)):
    with db() as conn:
        _require_profile(conn, profile_id, user)
        return _load_tasks(conn, profile_id)

@router.patch("/profiles/{profile_id}/tasks/{task_id}", response_model=StoredTask)
def update_task(profile_id: int, task_id: str, t: TaskUpdate, user: User = Depends(current_user)):
    with db() as conn:
        _require_profile(conn, profile_id, user)
        where, params = "profile_id = ? AND id = ?", (profile_id, task_id)
        if conn.execute(f"SELECT 1 FROM tasks WHERE {where}", params).fetchone() is None:
            raise HTTPException(404, "Task not found")
        _update(conn, "tasks", t.model_dump(exclude_unset=True), where, params)
        return StoredTask(**dict(conn.execute(f"SELECT * FROM tasks WHERE {where}", params).fetchone()))

@router.delete("/profiles/{profile_id}/tasks/{task_id}", status_code=204)
def delete_task(profile_id: int, task_id: str, user: User = Depends(current_user)):
    with db() as conn:
        _require_profile(conn, profile_id, user)
        cur = conn.execute("DELETE FROM tasks WHERE profile_id = ? AND id = ?", (profile_id, task_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "Task not found")
    return Response(status_code=204)

#plans
@router.post("/profiles/{profile_id}/plans", response_model=SavedPlan, status_code=201)
def create_plan(profile_id: int, req: PlanCreate, user: User = Depends(current_user)):
    with db() as conn:
        profile = _require_profile(conn, profile_id, user)
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
def list_plans(profile_id: int, user: User = Depends(current_user)):
    with db() as conn:
        _require_profile(conn, profile_id, user)
        rows = conn.execute(
            "SELECT * FROM plans WHERE profile_id = ? ORDER BY id DESC", (profile_id,)).fetchall()
        return [_row_to_plan(r) for r in rows]

def _require_plan(conn, plan_id: int, user: User):
    row = conn.execute(
        """SELECT pl.* FROM plans pl JOIN profiles pr ON pr.id = pl.profile_id
           WHERE pl.id = ? AND pr.user_id = ?""", (plan_id, user.id)).fetchone()
    if row is None:
        raise HTTPException(404, "Plan not found")
    return row

@router.get("/plans/{plan_id}", response_model=SavedPlan)
def get_plan(plan_id: int, user: User = Depends(current_user)):
    with db() as conn:
        return _row_to_plan(_require_plan(conn, plan_id, user))

@router.delete("/plans/{plan_id}", status_code=204)
def delete_plan(plan_id: int, user: User = Depends(current_user)):
    with db() as conn:
        _require_plan(conn, plan_id, user)
        conn.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
    return Response(status_code=204)
