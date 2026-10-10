from __future__ import annotations

import pytest

from dream_rsi.benchmarks.autocorrelation import AutocorrelationEvaluator
from dream_rsi.benchmarks.circle_packing import Circle, CirclePackingEvaluator
from dream_rsi.benchmarks.lasso import LassoEvaluator
from dream_rsi.benchmarks.sum_difference import SumDifferenceEvaluator
from dream_rsi.benchmarks.tree_generator import generate_benchmark_discovery_tree


def test_sum_difference_evaluation() -> None:
    seed_set = SumDifferenceEvaluator.generate_more_sums_than_differences_seed()
    res = SumDifferenceEvaluator.evaluate(seed_set)
    assert res.is_valid is True
    assert res.size == 8
    assert res.sumset_size > 0
    assert res.diffset_size > 0
    assert res.gamma_score > 0.5


def test_sum_difference_invalid() -> None:
    res = SumDifferenceEvaluator.evaluate([1])
    assert res.is_valid is False
    assert res.gamma_score == 0.0


def test_circle_packing_evaluation() -> None:
    circles = CirclePackingEvaluator.generate_regular_grid(26)
    res = CirclePackingEvaluator.evaluate(circles)
    assert res.is_valid is True
    assert res.num_circles == 26
    assert res.sum_radii > 1.0


def test_circle_packing_overlap_violation() -> None:
    circles = [
        Circle(x=0.5, y=0.5, r=0.4),
        Circle(x=0.5, y=0.5, r=0.4),
    ]
    res = CirclePackingEvaluator.evaluate(circles)
    assert res.is_valid is False
    assert res.sum_radii == 0.0
    assert len(res.violations) > 0


def test_autocorrelation_evaluation() -> None:
    grid = AutocorrelationEvaluator.uniform_density_baseline(51)
    res = AutocorrelationEvaluator.evaluate(grid)
    assert res.is_valid is True
    assert res.phi_1 > 0.0
    assert res.phi_2 > 0.0
    assert res.phi_3 > 0.0
    assert abs(res.integral_mass - 1.0) < 1e-3


def test_lasso_coordinate_descent_and_evaluation() -> None:
    x_rows = [
        [1.0, 0.5],
        [0.5, 1.0],
        [-0.5, 0.2],
        [0.8, -0.4],
    ]
    y = [1.2, 0.8, -0.3, 0.5]
    lambdas = [0.1, 0.05]

    sol = LassoEvaluator.solve_coordinate_descent(x_rows, y, lambdas, max_iter=200)
    assert len(sol) == 2
    assert len(sol[0]) == 2

    res = LassoEvaluator.evaluate_solution(
        x_rows=x_rows,
        y=y,
        lam_path=lambdas,
        candidate_path=sol,
        runtime_ms=5.0,
    )
    assert res.is_correct is True
    assert res.search_score > 0.0


def test_generate_benchmark_discovery_tree() -> None:
    for problem in ["sum_difference", "circle_packing", "autocorrelation"]:
        tree = generate_benchmark_discovery_tree(
            problem_type=problem,
            tree_id=f"tree_{problem}",
            num_branches=3,
            depth_per_branch=3,
        )
        assert tree.root_id == "root"
        assert len(tree.nodes) == 1 + (3 * 3)
        assert tree.metadata["problem"] == problem
        tree.check_integrity()
