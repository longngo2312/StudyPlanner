#app/services/runner.py
#runs a knapsack solver (dp, greedy, brute force) and times it; compare runs all three on the same input

import time
from app.models import SolveRequest, SolveResult, CompareRequest, CompareResult
from app.services.algorithms import ALGORITHMS
from fastapi import HTTPException

BRUTE_LIMIT = 20   #capping brute force since it is O(n * 2^n)

def run(req: SolveRequest) -> SolveResult:
    if req.algorithm == "brute" and len(req.tasks) > BRUTE_LIMIT:
        raise HTTPException(400, f"Brute force is limited to {BRUTE_LIMIT} tasks")
    fn = ALGORITHMS[req.algorithm]
    start = time.perf_counter()
    selected, benefit, used = fn(req.tasks, req.capacity)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return SolveResult(
        selected_ids=selected,
        total_benefit=benefit,
        total_time=used,
        runtime_ms=elapsed_ms,
        algorithm=req.algorithm,
    )

def compare(req: CompareRequest) -> CompareResult:
    results, skipped = [], {}
    for name in ("dp", "greedy", "brute"):
        if name == "brute" and len(req.tasks) > BRUTE_LIMIT:
            skipped[name] = f"{len(req.tasks)} tasks exceeds the brute force limit of {BRUTE_LIMIT}"
            continue
        results.append(run(SolveRequest(tasks=req.tasks, capacity=req.capacity, algorithm=name)))

    best = max((r.total_benefit for r in results), default=0.0)
    for r in results:
        r.quality = r.total_benefit / best if best > 0 else 1.0   #1.0 = matches the best found
    return CompareResult(results=results, skipped=skipped, best_benefit=best)
