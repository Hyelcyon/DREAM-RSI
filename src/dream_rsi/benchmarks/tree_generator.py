from __future__ import annotations

import random
from dream_rsi.benchmarks.autocorrelation import AutocorrelationEvaluator
from dream_rsi.benchmarks.circle_packing import CirclePackingEvaluator
from dream_rsi.benchmarks.lasso import LassoEvaluator
from dream_rsi.benchmarks.sum_difference import SumDifferenceEvaluator
from dream_rsi.core.models import DiscoveryTree, Observation, TreeNode


def generate_benchmark_discovery_tree(
    problem_type: str = "sum_difference",
    tree_id: str = "tree_bench_01",
    num_branches: int = 4,
    depth_per_branch: int = 4,
    seed: int = 42,
) -> DiscoveryTree:
    """Synthesizes a realistic discovery tree grounded in real scientific benchmarks."""
    rng = random.Random(seed)

    baseline_score = 0.5
    if problem_type == "sum_difference":
        seed_set = SumDifferenceEvaluator.generate_more_sums_than_differences_seed()
        eval_res = SumDifferenceEvaluator.evaluate(seed_set)
        baseline_score = eval_res.gamma_score
    elif problem_type == "circle_packing":
        circles = CirclePackingEvaluator.generate_regular_grid(26)
        pack_res = CirclePackingEvaluator.evaluate(circles)
        baseline_score = pack_res.sum_radii
    elif problem_type == "autocorrelation":
        grid = AutocorrelationEvaluator.uniform_density_baseline(101)
        ac_res = AutocorrelationEvaluator.evaluate(grid)
        baseline_score = 2.0 - ac_res.phi_1
    elif problem_type == "lasso":
        x_rows = [
            [1.0, 0.4, -0.2],
            [0.5, 0.9, 0.1],
            [-0.3, 0.2, 0.8],
            [0.7, -0.5, 0.3],
            [-0.2, 0.6, -0.4],
        ]
        y = [1.1, 0.7, -0.2, 0.6, -0.1]
        lambdas = [0.2, 0.1, 0.05]
        cand_path = LassoEvaluator.solve_coordinate_descent(x_rows, y, lambdas, max_iter=100)
        lasso_res = LassoEvaluator.evaluate_solution(x_rows, y, lambdas, cand_path, runtime_ms=10.0)
        baseline_score = lasso_res.search_score

    root_node = TreeNode(
        node_id="root",
        parent_id=None,
        branch_id=0,
        attempt_index=0,
        depth=0,
        observation=Observation(
            branch=0,
            attempt=0,
            score=baseline_score,
            evaluated=True,
            valid=True,
            fail_class="ok",
            delta_vs_baseline=0.0,
            delta_vs_parent=0.0,
        ),
        artifact_code=f"# Baseline root for {problem_type}",
    )

    tree = DiscoveryTree(
        tree_id=tree_id,
        root_id="root",
        metadata={
            "problem": problem_type,
            "baseline_score": baseline_score,
        },
    )
    tree.add_node(root_node)

    for b in range(1, num_branches + 1):
        parent_id = "root"
        curr_score = baseline_score
        is_branch_dead = False

        for d in range(1, depth_per_branch + 1):
            node_id = f"node_b{b}_d{d}"
            roll = rng.random()

            if is_branch_dead:
                obs = Observation(
                    branch=b,
                    attempt=d,
                    score=curr_score,
                    evaluated=False,
                    valid=False,
                    fail_class="runtime_error",
                    error="Branch already halted.",
                )
            elif roll < 0.15:
                obs = Observation(
                    branch=b,
                    attempt=d,
                    score=curr_score,
                    evaluated=True,
                    valid=False,
                    fail_class="shape_mismatch",
                    error="Dimensionality assertion failed.",
                    delta_vs_parent=0.0,
                    delta_vs_baseline=curr_score - baseline_score,
                )
            elif roll < 0.25:
                obs = Observation(
                    branch=b,
                    attempt=d,
                    score=curr_score,
                    evaluated=True,
                    valid=False,
                    fail_class="environment_failure",
                    error="Device memory allocation failure.",
                )
                is_branch_dead = True
            else:
                gain = rng.uniform(0.01, 0.08) if roll > 0.5 else rng.uniform(-0.02, 0.02)
                new_score = max(0.1, curr_score + gain)
                obs = Observation(
                    branch=b,
                    attempt=d,
                    score=new_score,
                    evaluated=True,
                    valid=True,
                    fail_class="ok",
                    delta_vs_parent=new_score - curr_score,
                    delta_vs_baseline=new_score - baseline_score,
                )
                curr_score = new_score

            node = TreeNode(
                node_id=node_id,
                parent_id=parent_id,
                branch_id=b,
                attempt_index=d,
                depth=d,
                observation=obs,
                artifact_code=f"# Attempt {d} on branch {b}",
            )
            tree.add_node(node)
            parent_id = node_id

    return tree
