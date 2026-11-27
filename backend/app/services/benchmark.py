#app/services/benchmark.py
#benchmark runner, generates random task sets, suns all algorithms on same input
#averages runtime, benefit, and quality over multiple repeats

from statistics import mean
from app.models import BenchmarkRequest, BenchmarkResult, BenchmarkRow, SolveRequest
from app.services.datagen import generate_scored_tasks
from app.services.runner import run

def run_benchmark(req: BenchmarkRequest) -> BenchmarkResult:
    rows: list[BenchmarkRow] = []
    for n in req.task_counts:
        for cap in req.capacities:
            algos = ["dp", "greedy"] + (["brute"] if n <= req.brute_max_n else [])
            times = {a: [] for a in algos}
            benefits = {a: [] for a in algos}
            qualities = {a: [] for a in algos}

            for rep in range(req.repeats):
                tasks = generate_scored_tasks(n, seed=req.seed + rep)
                results = {a: run(SolveRequest(tasks=tasks, capacity=cap, algorithm=a))
                           for a in algos}
                optimal = results["dp"].total_benefit
                for a, res in results.items():
                    times[a].append(res.runtime_ms)
                    benefits[a].append(res.total_benefit)
                    qualities[a].append(res.total_benefit / optimal if optimal > 0 else 1.0)

            for a in algos:
                rows.append(BenchmarkRow(
                    n=n, capacity=cap, algorithm=a,
                    avg_runtime_ms=mean(times[a]),
                    avg_benefit=mean(benefits[a]),
                    avg_quality=mean(qualities[a]),
                    repeats=req.repeats,
                ))
    return BenchmarkResult(rows=rows)