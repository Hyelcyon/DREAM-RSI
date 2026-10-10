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
