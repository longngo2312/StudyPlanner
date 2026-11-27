#scripts/plot_benchmarks.py
#benchmark plots to run the benchmark without server or login
#saves 3 PNGs + CSV of runtime vs task count, capacity, and greedy solution quality to backend/benchmark_plots
#run from backend: python -m scripts.plot_benchmarks

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")   # write image files, don't open a window
import matplotlib.pyplot as plt

from app.models import BenchmarkRequest
from app.services.benchmark import run_benchmark

OUT = Path(__file__).resolve().parent.parent / "benchmark_plots"
STYLE = {   #algorithm: (label, color, marker)
    "dp": ("DP", "tab:blue", "o"),
    "greedy": ("Greedy", "tab:orange", "s"),
    "brute": ("Brute force", "tab:red", "^"),
}

def series(rows, algo, x, y, **where):
    """Sorted (x, y) points for one algorithm, filtered by e.g. capacity=90."""
    pts = sorted((getattr(r, x), getattr(r, y)) for r in rows
                 if r.algorithm == algo and all(getattr(r, k) == v for k, v in where.items()))
    return [p[0] for p in pts], [p[1] for p in pts]

def plot_runtime_vs_n(rows, capacity, path):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for algo, (label, color, marker) in STYLE.items():
        xs, ys = series(rows, algo, "n", "avg_runtime_ms", capacity=capacity)
        if xs:
            ax.plot(xs, ys, marker=marker, color=color, label=label)
    ax.set_yscale("log")
    ax.set_xlabel("Number of tasks (n)")
    ax.set_ylabel("Average runtime (ms, log scale)")
    ax.set_title(f"Runtime vs. number of tasks (capacity = {capacity} blocks)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)

def plot_runtime_vs_capacity(rows, n, path):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for algo in ("dp", "greedy"):
        label, color, marker = STYLE[algo]
        xs, ys = series(rows, algo, "capacity", "avg_runtime_ms", n=n)
        ax.plot(xs, ys, marker=marker, color=color, label=label)
    ax.set_xlabel("Capacity (time blocks)")
    ax.set_ylabel("Average runtime (ms)")
    ax.set_title(f"Runtime vs. capacity (n = {n} tasks)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)

def plot_quality(rows, capacities, path):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for cap in capacities:
        xs, ys = series(rows, "greedy", "n", "avg_quality", capacity=cap)
        ax.plot(xs, ys, marker="s", label=f"Greedy, capacity {cap}")
    ax.axhline(1.0, color="tab:blue", linestyle="--", label="DP / brute force (optimal)")
    ax.set_xlabel("Number of tasks (n)")
    ax.set_ylabel("Benefit relative to optimal")
    ax.set_title("Greedy solution quality")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)

def write_csv(rows, path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["n", "capacity", "algorithm", "avg_runtime_ms", "avg_benefit", "avg_quality", "repeats"])
        for r in rows:
            w.writerow([r.n, r.capacity, r.algorithm, r.avg_runtime_ms,
                        r.avg_benefit, r.avg_quality, r.repeats])

def main():
    OUT.mkdir(exist_ok=True)
    capacities = [30, 90]   #two personas: Part-time Working Adult, Full-time Engineering Student

    print("Running sweep 1: task count (brute force up to n=16)...")
    by_n = run_benchmark(BenchmarkRequest(
        task_counts=[4, 8, 10, 12, 14, 16, 20, 30, 40, 50],
        capacities=capacities, repeats=5, brute_max_n=16)).rows

    print("Running sweep 2: capacity...")
    by_cap = run_benchmark(BenchmarkRequest(
        task_counts=[30], capacities=[30, 60, 90, 150, 300, 600, 1200],
        repeats=5, brute_max_n=0)).rows

    plot_runtime_vs_n(by_n, 90, OUT / "runtime_vs_n.png")
    plot_runtime_vs_capacity(by_cap, 30, OUT / "runtime_vs_capacity.png")
    plot_quality(by_n, capacities, OUT / "greedy_quality.png")
    write_csv(by_n + by_cap, OUT / "benchmark_results.csv")
    print(f"Saved plots and CSV to {OUT}")

if __name__ == "__main__":
    main()