#app/services/algorithms.py
#0-1 knapsack solvers: dynamic programming, greedy, brute force
#all share one interface: (tasks, capacity) -> (selected_ids, total_benefit, total_time)
#tasks have .id, .duration (int > 0, the weight) and .benefit (float >= 0, the value)

from itertools import combinations

def dp(tasks, capacity):
    """Bottom-up 0-1 knapsack. O(nW) time.
    best[w] = max benefit using at most w time units over the tasks seen so far (O(W) space).
    keep[i][w] records whether task i was taken at capacity w, so the chosen set can be
    rebuilt afterwards (n*W bytes; drop it if only the optimal benefit is needed)."""
    best = [0.0] * (capacity + 1)
    keep = []
    for t in tasks:
        row = bytearray(capacity + 1)
        #go right to left so each task is used at most once (the "0-1" part)
        for w in range(capacity, t.duration - 1, -1):
            take = best[w - t.duration] + t.benefit
            if take > best[w]:
                best[w] = take
                row[w] = 1
        keep.append(row)

    #walk back from the full capacity to recover which tasks were chosen
    chosen, w = [], capacity
    for i in range(len(tasks) - 1, -1, -1):
        if keep[i][w]:
            chosen.append(tasks[i])
            w -= tasks[i].duration
    chosen.reverse()
    return [t.id for t in chosen], sum(t.benefit for t in chosen), sum(t.duration for t in chosen)

def greedy(tasks, capacity):
    """Take tasks by benefit per time unit, highest first, while they fit.
    O(n log n) time, O(n) space. Fast, but not always optimal."""
    ordered = sorted(tasks, key=lambda t: t.benefit / t.duration, reverse=True)
    chosen, used, benefit = [], 0, 0.0
    for t in ordered:
        if used + t.duration <= capacity:
            chosen.append(t.id)
            used += t.duration
            benefit += t.benefit
    return chosen, benefit, used

def brute(tasks, capacity):
    """Try every subset and keep the best one that fits. O(n * 2^n) time, O(n) space.
    Always optimal, so it is the reference the other two are checked against."""
    best_set, best_benefit = (), 0.0
    for k in range(1, len(tasks) + 1):
        for subset in combinations(tasks, k):
            if sum(t.duration for t in subset) <= capacity:
                b = sum(t.benefit for t in subset)
                if b > best_benefit:
                    best_set, best_benefit = subset, b
    return [t.id for t in best_set], best_benefit, sum(t.duration for t in best_set)

ALGORITHMS = {"dp": dp, "greedy": greedy, "brute": brute}
