#app/services/runner.py
#service to run the knapsack problem solver using different algorithms (greedy, dynamic programming, brute force)
#currently uses a placeholder greedy algorithm for testing purposes

import time
from app.models import SolveRequest, SolveResult, CompareRequest, CompareResult

BRUTE_FORCE_LIMIT = 20  #max number of tasks for brute force algorithm

def compare(req: CompareRequest) -> CompareResult:
    results, skipped = [], {}
    for name in ("dp", "greedy", "brute"):
        if name == "brute" and len(req.tasks) > BRUTE_FORCE_LIMIT:
            skipped[name] = f"{len(req.tasks)} tasks exceeds the brute force limit of {BRUTE_FORCE_LIMIT}"
            continue
        results.append(run(SolveRequest(tasks=req.tasks, capacity=req.capacity, algorithm=name)))

    best = max((r.total_benefit for r in results), default=0.0)
    for r in results:
        r.quality = r.total_benefit / best if best > 0 else 1.0 #quality: each algorithm's result relative to the best found
    return CompareResult(results=results, skipped=skipped, best_benefit=best)

#[testing] function to solve the knapsack problem using a greedy algorithm
def greedy(tasks, capacity):
    ordered = sorted(tasks, key=lambda t: t.benefit / t.duration, reverse=True)
    chosen, used, benefit = [], 0, 0.0
    for t in ordered:
        if used + t.duration <= capacity:
            chosen.append(t.id)
            used += t.duration
            benefit += t.benefit
    return chosen, benefit, used

#todo: replace "dp" and "brute" with actual algo implementations
ALGORITHMS = {"greedy": greedy, "dp": greedy, "brute": greedy}

def run(req: SolveRequest) -> SolveResult:
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

BRUTE_LIMIT = 20   #capping brute force since it is O(n * 2^n)

def compare(req: CompareRequest) -> CompareResult:
    results, skipped = [], {}
    for name in ("dp", "greedy", "brute"):
        if name == "brute" and len(req.tasks) > BRUTE_LIMIT:
            skipped[name] = f"{len(req.tasks)} tasks exceeds the brute force limit of {BRUTE_LIMIT}"
            continue
        results.append(run(SolveRequest(tasks=req.tasks, capacity=req.capacity, algorithm=name)))

    best = max((r.total_benefit for r in results), default=0.0)
    for r in results:
        r.quality = r.total_benefit / best if best > 0 else 1.0
    return CompareResult(results=results, skipped=skipped, best_benefit=best)