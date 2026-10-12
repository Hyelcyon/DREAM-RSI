from __future__ import annotations

import pytest

from dream_rsi.optimizer.optimizer import FrontierPoint, PolicyOptimizer


def test_select_cross_cycle_beta_improving() -> None:
    optimizer = PolicyOptimizer()
    sweep = [
        FrontierPoint(
            beta=0.2, mean_replay_score=0.7, mean_pareto_reward=0.6, mean_pareto_auc=0.7, mean_parallel_penalty=0.2
        ),
        FrontierPoint(
            beta=0.6, mean_replay_score=0.9, mean_pareto_reward=0.85, mean_pareto_auc=0.9, mean_parallel_penalty=0.1
        ),
    ]

    res = optimizer.select_cross_cycle_beta(
        history_scores=[0.5, 0.7, 0.85],
        current_beta=0.6,
        sweep_frontier=sweep,
    )
    assert res.recommended_beta == 0.6
    assert res.is_adjusted is False
    assert "actively improving" in res.reason


def test_select_cross_cycle_beta_plateau_raise() -> None:
    optimizer = PolicyOptimizer()
    sweep = [
        FrontierPoint(
            beta=0.4, mean_replay_score=0.6, mean_pareto_reward=0.5, mean_pareto_auc=0.6, mean_parallel_penalty=0.2
        ),
        FrontierPoint(
            beta=0.8, mean_replay_score=0.95, mean_pareto_reward=0.9, mean_pareto_auc=0.95, mean_parallel_penalty=0.1
        ),
    ]

    res = optimizer.select_cross_cycle_beta(
        history_scores=[0.7, 0.7, 0.7],
        current_beta=0.5,
        sweep_frontier=sweep,
    )
    assert res.recommended_beta > 0.5
    assert res.is_adjusted is True
    assert "plateaued" in res.reason


def test_select_cross_cycle_beta_insufficient_history() -> None:
    optimizer = PolicyOptimizer()
    res = optimizer.select_cross_cycle_beta(
        history_scores=[],
        current_beta=0.5,
        sweep_frontier=[],
    )
    assert res.recommended_beta == 0.6
    assert "insufficient" in res.reason.lower()


def test_pareto_dominance_filtering() -> None:
    p_high_score = FrontierPoint(
        beta=0.8, mean_replay_score=1.2, mean_pareto_reward=0.7, mean_pareto_auc=1.1, mean_parallel_penalty=0.2
    )
    p_dominated = FrontierPoint(
        beta=0.4, mean_replay_score=1.0, mean_pareto_reward=0.6, mean_pareto_auc=0.9, mean_parallel_penalty=0.3
    )
    p_high_reward = FrontierPoint(
        beta=0.2, mean_replay_score=1.1, mean_pareto_reward=0.85, mean_pareto_auc=1.2, mean_parallel_penalty=0.1
    )

    optimizer = PolicyOptimizer()
    assert optimizer.is_dominated(p_dominated, p_high_score) is True
    assert optimizer.is_dominated(p_high_score, p_dominated) is False
    assert optimizer.is_dominated(p_high_score, p_high_reward) is False

    frontier = optimizer.filter_non_dominated([p_high_score, p_dominated, p_high_reward])
    assert len(frontier) == 2
    assert p_dominated not in frontier
    assert p_high_score in frontier
    assert p_high_reward in frontier


def test_filter_non_dominated_empty_and_single() -> None:
    optimizer = PolicyOptimizer()
    assert optimizer.filter_non_dominated([]) == []

    p = FrontierPoint(
        beta=0.5, mean_replay_score=1.0, mean_pareto_reward=1.0, mean_pareto_auc=1.0, mean_parallel_penalty=0.0
    )
    res = optimizer.filter_non_dominated([p])
    assert len(res) == 1
    assert res[0] == p


def test_filter_non_dominated_tolerances_and_duplicates() -> None:
    optimizer = PolicyOptimizer()

    p_base = FrontierPoint(
        beta=0.1, mean_replay_score=1.0, mean_pareto_reward=1.0, mean_pareto_auc=1.0, mean_parallel_penalty=0.0
    )
    p_dup = FrontierPoint(
        beta=0.2, mean_replay_score=1.0, mean_pareto_reward=1.0, mean_pareto_auc=1.0, mean_parallel_penalty=0.0
    )
    res_dup = optimizer.filter_non_dominated([p_base, p_dup])
    assert len(res_dup) == 2

    p_slightly_lower_score_high_reward = FrontierPoint(
        beta=0.3, mean_replay_score=1.0 - 0.5e-9, mean_pareto_reward=1.0 + 2e-6, mean_pareto_auc=1.0, mean_parallel_penalty=0.0
    )
    res_tol1 = optimizer.filter_non_dominated([p_base, p_slightly_lower_score_high_reward])
    assert p_base not in res_tol1
    assert p_slightly_lower_score_high_reward in res_tol1

    p_too_low_score = FrontierPoint(
        beta=0.4, mean_replay_score=1.0 - 2e-9, mean_pareto_reward=2.0, mean_pareto_auc=1.0, mean_parallel_penalty=0.0
    )
    p_high = FrontierPoint(
        beta=0.5, mean_replay_score=1.0, mean_pareto_reward=1.0, mean_pareto_auc=1.0, mean_parallel_penalty=0.0
    )
    res_tol2 = optimizer.filter_non_dominated([p_high, p_too_low_score])
    assert len(res_tol2) == 2


def test_filter_non_dominated_randomized_equivalence() -> None:
    import random

    def pairwise_reference(points: list[FrontierPoint]) -> list[FrontierPoint]:
        non_dom: list[FrontierPoint] = []
        for p in points:
            if not any(PolicyOptimizer.is_dominated(p, other) for other in points if other is not p):
                non_dom.append(p)
        non_dom.sort(key=lambda x: (x.mean_replay_score, x.mean_pareto_reward), reverse=True)
        return non_dom

    rng = random.Random(1337)
    test_points = [
        FrontierPoint(
            beta=round(rng.random(), 3),
            mean_replay_score=round(rng.uniform(0.5, 2.0), rng.choice([2, 5, 7, 10])),
            mean_pareto_reward=round(rng.uniform(0.1, 1.5), rng.choice([2, 5, 7, 10])),
            mean_pareto_auc=1.0,
            mean_parallel_penalty=0.05,
        )
        for _ in range(300)
    ]

    expected = pairwise_reference(test_points)
    actual = PolicyOptimizer.filter_non_dominated(test_points)
    assert len(actual) == len(expected)
    for exp, act in zip(expected, actual):
        assert exp == act

