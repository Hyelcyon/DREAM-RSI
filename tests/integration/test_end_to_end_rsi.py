from __future__ import annotations

from pathlib import Path

from dream_rsi.core.models import (
    DiscoveryTree,
    GridPlanningContext,
    HistorySummaryItem,
    Observation,
    TreeNode,
)
from dream_rsi.optimizer.optimizer import PolicyOptimizer
from dream_rsi.optimizer.policy import DynamicPortfolioPolicy
from dream_rsi.replay.simulator import ReplaySimulator
from dream_rsi.storage.store import JsonFileHistoryStore


def create_synthetic_tree(tree_id: str, depth: int, max_score: float) -> DiscoveryTree:
    root = TreeNode(
        node_id=f"{tree_id}_r",
        observation=Observation(branch=0, attempt=0, score=0.1, evaluated=True),
    )
    tree = DiscoveryTree(tree_id=tree_id, root_id=root.node_id)
    tree.add_node(root)

    prev_id = root.node_id
    for d in range(1, depth + 1):
        score = round(0.1 + (max_score - 0.1) * (d / depth), 3)
        node = TreeNode(
            node_id=f"{tree_id}_b1_d{d}",
            parent_id=prev_id,
            branch_id=1,
            attempt_index=d - 1,
            depth=d,
            observation=Observation(branch=1, attempt=d - 1, score=score, evaluated=True),
        )
        tree.add_node(node)
        prev_id = node.node_id

    err_node = TreeNode(
        node_id=f"{tree_id}_b2_d1",
        parent_id=root.node_id,
        branch_id=2,
        attempt_index=0,
        depth=1,
        observation=Observation(
            branch=2,
            attempt=0,
            score=0.05,
            evaluated=True,
            fail_class="compile_error",
            error="syntax error",
        ),
    )
    tree.add_node(err_node)

    return tree


def test_closed_loop_recursive_self_improvement(tmp_path: Path) -> None:
    store = JsonFileHistoryStore(base_dir=tmp_path)
    simulator = ReplaySimulator()
    optimizer = PolicyOptimizer(simulator=simulator)

    pi_0 = DynamicPortfolioPolicy(name="pi_0", beta=0.1, worker_cap=3)
    tree_0 = create_synthetic_tree("episode_0", depth=3, max_score=0.7)
    store.save_tree(tree_0)

    eval_0 = simulator.run_episode(pi_0, tree_0, max_budget=20)
    assert eval_0.max_score >= 0.7
    assert eval_0.replay_score > 0

    candidates = [
        DynamicPortfolioPolicy(name="pi_cand_exploit", beta=0.8, worker_cap=3),
        DynamicPortfolioPolicy(name="pi_cand_balanced", beta=0.5, worker_cap=3),
        DynamicPortfolioPolicy(name="pi_cand_wide", beta=0.2, worker_cap=3),
    ]

    pi_1_star, comp_1 = optimizer.select_optimal_policy(
        candidate_policies=candidates,
        baseline_policy=pi_0,
        trees=[tree_0],
        max_budget=20,
    )

    assert comp_1.monotonicity_verified is True
    assert comp_1.selected_replay_score >= comp_1.baseline_replay_score

    tree_1 = create_synthetic_tree("episode_1", depth=5, max_score=0.95)
    store.save_tree(tree_1)

    eval_1 = simulator.run_episode(pi_1_star, tree_1, max_budget=20)
    assert eval_1.max_score >= 0.95

    trees_h1 = [tree_0, tree_1]
    candidates_2 = [
        DynamicPortfolioPolicy(name="pi_cand_high_beta", beta=0.9, worker_cap=4),
        DynamicPortfolioPolicy(name="pi_cand_mid_beta", beta=0.6, worker_cap=4),
    ]

    pi_2_star, comp_2 = optimizer.select_optimal_policy(
        candidate_policies=candidates_2,
        baseline_policy=pi_1_star,
        trees=trees_h1,
        max_budget=20,
    )

    assert pi_2_star.name == comp_2.selected_policy
    assert comp_2.monotonicity_verified is True
    assert comp_2.selected_replay_score >= comp_2.baseline_replay_score

    manifest = store.get_manifest()
    assert manifest.total_trees == 2

    history_summary = [
        HistorySummaryItem(
            tree_id="episode_0",
            max_depth=3,
            best_score=0.7,
        ),
        HistorySummaryItem(
            tree_id="episode_1",
            max_depth=5,
            best_score=0.95,
        ),
    ]
    ctx = GridPlanningContext(history=history_summary, worker_cap=10)
    next_grid = DynamicPortfolioPolicy.plan_grid(ctx)

    assert next_grid.branch_count >= 1
    assert next_grid.refine_count >= 1
    assert "High success history" in next_grid.reason
