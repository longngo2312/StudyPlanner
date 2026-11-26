#tests/test_algorithms.py
#correctness tests for the knapsack solvers (dp, greedy, brute force)

import random
import pytest
from app.models import Task
from app.services.algorithms import dp, greedy, brute

def T(id, duration, benefit):
    return Task(id=id, name=id, duration=duration, benefit=benefit)

ALL = [dp, greedy, brute]
OPTIMAL = [dp, brute]

@pytest.mark.parametrize("fn", ALL)
def test_empty_task_list(fn):
    assert fn([], 10) == ([], 0.0, 0)

@pytest.mark.parametrize("fn", ALL)
def test_zero_capacity(fn):
    assert fn([T("a", 1, 5)], 0) == ([], 0.0, 0)

@pytest.mark.parametrize("fn", ALL)
def test_single_task_fits_exactly(fn):
    assert fn([T("a", 3, 5)], 3) == (["a"], 5.0, 3)

@pytest.mark.parametrize("fn", ALL)
def test_task_bigger_than_capacity_is_skipped(fn):
    assert fn([T("big", 9, 100), T("small", 2, 1)], 8) == (["small"], 1.0, 2)

@pytest.mark.parametrize("fn", OPTIMAL)
def test_beats_greedy_on_classic_counterexample(fn):
    #greedy takes "a" first (best ratio, 6/unit), which blocks the better pair b+c
    tasks = [T("a", 1, 6), T("b", 5, 25), T("c", 5, 25)]
    assert greedy(tasks, 10)[1] == 31
    ids, benefit, used = fn(tasks, 10)
    assert sorted(ids) == ["b", "c"] and benefit == 50 and used == 10

@pytest.mark.parametrize("fn", OPTIMAL)
def test_equal_ratios(fn):
    #every task is worth 2 per unit, so the best plan fills all 6 units (greedy may leave a gap)
    tasks = [T("a", 2, 4), T("b", 3, 6), T("c", 4, 8)]
    _, benefit, used = fn(tasks, 6)
    assert used == 6 and benefit == 12

def test_random_cases_dp_matches_brute():
    rng = random.Random(4110)
    for _ in range(300):
        tasks = [T(str(i), rng.randint(1, 10), round(rng.uniform(0, 500), 2))
                 for i in range(rng.randint(0, 12))]
        cap = rng.randint(0, 40)
        by_id = {t.id: t for t in tasks}
        best = brute(tasks, cap)[1]
        for fn in ALL:
            ids, benefit, used = fn(tasks, cap)
            #result is a valid selection: no repeats, fits, totals add up
            assert len(ids) == len(set(ids))
            assert used == sum(by_id[i].duration for i in ids) <= cap
            assert benefit == pytest.approx(sum(by_id[i].benefit for i in ids))
            if fn is greedy:
                assert benefit <= best + 1e-9
            else:
                assert benefit == pytest.approx(best)
