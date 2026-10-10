from __future__ import annotations

import pytest

from dream_rsi.benchmarks.tree_generator import generate_benchmark_discovery_tree
from dream_rsi.optimizer.policy import OptimalPolicy
from dream_rsi.replay.question import QuestionAPI


def test_optimal_policy_schedule_mapping() -> None:
    pol_low = OptimalPolicy(config={"beta": 0.2})
    sched_low = pol_low._schedule(0.2)
    assert sched_low["patience"] <= 3
    assert sched_low["min_gain"] > 0.0

    pol_high = OptimalPolicy(config={"beta": 0.9})
    sched_high = pol_high._schedule(0.9)
    assert sched_high["patience"] >= 5
    assert sched_high["exploit_ratio"] >= 0.7


def test_optimal_policy_step_and_solve() -> None:
    tree = generate_benchmark_discovery_tree(
        problem_type="sum_difference",
        tree_id="t_solve_test",
        num_branches=3,
        depth_per_branch=3,
    )
    question = QuestionAPI(tree=tree, max_parallelism=2, max_budget=10)

    policy = OptimalPolicy(config={"beta": 0.6, "worker_cap": 2})
    revealed = policy.solve(question, budget=8)

    assert len(revealed) > 0
    assert question.probes_spent <= 8
    assert len(question.observed()) > 1
