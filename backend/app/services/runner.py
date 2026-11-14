#app/services/runner.py
#service to run the knapsack problem solver using different algorithms (greedy, dynamic programming, brute force)
#currently uses a placeholder greedy algorithm for testing purposes

import time
from app.models import SolveRequest, SolveResult

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