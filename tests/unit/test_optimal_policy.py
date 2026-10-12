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


def test_optimal_policy_no_duplicates_in_step_batch() -> None:
    tree = generate_benchmark_discovery_tree(
        problem_type="circle_packing",
        tree_id="t_uniq_test",
        num_branches=4,
        depth_per_branch=3,
    )
    question = QuestionAPI(tree=tree, max_parallelism=4, max_budget=10)
    policy = OptimalPolicy(config={"beta": 0.5, "worker_cap": 4})

    for _ in range(3):
        if question.is_exhausted():
            break
        batch = policy.step(question)
        if not batch:
            break
        assert len(batch) == len(set(batch))
        question.probe_batch(batch)


def test_optimal_policy_incremental_trajectory_indexing() -> None:
    tree = generate_benchmark_discovery_tree(
        problem_type="sum_difference",
        tree_id="t_inc_test",
        num_branches=3,
        depth_per_branch=3,
    )
    question = QuestionAPI(tree=tree, max_parallelism=3, max_budget=10)
    policy = OptimalPolicy(config={"beta": 0.5, "worker_cap": 3})

    trajs1 = policy.reconstruct_trajectories(question)
    assert len(trajs1) == 0

    batch = policy.step(question)
    question.probe_batch(batch)
    trajs2 = policy.reconstruct_trajectories(question)
    assert len(trajs2) > 0

    policy.reset()
    assert len(policy._trajectories) == 0
