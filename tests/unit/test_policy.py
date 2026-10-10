import pytest
from dream_rsi.core.models import (
    DiscoveryTree,
    GridPlanningContext,
    HistorySummaryItem,
    Observation,
    TreeNode,
)
from dream_rsi.optimizer.optimizer import PolicyOptimizer
from dream_rsi.optimizer.policy import DynamicPortfolioPolicy
from dream_rsi.replay.question import QuestionAPI


@pytest.fixture
def complex_tree() -> DiscoveryTree:
    root = TreeNode(
        node_id="root",
        observation=Observation(branch=0, attempt=0, score=0.1, evaluated=True),
    )
    tree = DiscoveryTree(tree_id="tree_complex", root_id="root")
    tree.add_node(root)

    b1_1 = TreeNode(node_id="b1_1", parent_id="root", branch_id=1, attempt_index=0,
                    observation=Observation(branch=1, attempt=0, score=0.4, evaluated=True))
    b1_2 = TreeNode(node_id="b1_2", parent_id="b1_1", branch_id=1, attempt_index=1,
                    observation=Observation(branch=1, attempt=1, score=0.7, evaluated=True))
    b1_3 = TreeNode(node_id="b1_3", parent_id="b1_2", branch_id=1, attempt_index=2,
                    observation=Observation(branch=1, attempt=2, score=0.95, evaluated=True))

    b2_1 = TreeNode(node_id="b2_1", parent_id="root", branch_id=2, attempt_index=0,
                    observation=Observation(branch=2, attempt=0, score=0.2, evaluated=True,
                                            fail_class="compile_error", error="err"))
    b2_2 = TreeNode(node_id="b2_2", parent_id="b2_1", branch_id=2, attempt_index=1,
                    observation=Observation(branch=2, attempt=1, score=0.6, evaluated=True))

    b3_1 = TreeNode(node_id="b3_1", parent_id="root", branch_id=3, attempt_index=0,
                    observation=Observation(branch=3, attempt=0, score=0.1, evaluated=True,
                                            fail_class="runtime_error", error="oom"))

    for n in [b1_1, b1_2, b1_3, b2_1, b2_2, b3_1]:
        tree.add_node(n)

    return tree


def test_dynamic_portfolio_recovery_slot_constraint(complex_tree: DiscoveryTree) -> None:
    q = QuestionAPI(complex_tree, max_parallelism=5, max_budget=20)
    q.probe_batch(["root", "root"])
    q.probe_batch(["root"])

    policy = DynamicPortfolioPolicy(name="portfolio", beta=0.5, worker_cap=4, enable_recovery=True)
    batch = policy.step(q)

    recovery_nodes = {"b2_1", "b3_1"}
    recovery_count = sum(1 for node_id in batch if node_id in recovery_nodes)
    assert recovery_count <= 1


def test_plan_grid_deterministic() -> None:
    ctx = GridPlanningContext(
        history=[
            HistorySummaryItem(tree_id="t1", max_depth=5, best_score=0.9),
            HistorySummaryItem(tree_id="t2", max_depth=6, best_score=0.8),
        ],
        worker_cap=10,
        hard_max_branch_count=32,
        hard_max_refine_count=20,
    )
    plan1 = DynamicPortfolioPolicy.plan_grid(ctx)
    plan2 = DynamicPortfolioPolicy.plan_grid(ctx)

    assert plan1.branch_count == plan2.branch_count
    assert plan1.refine_count == plan2.refine_count
    assert plan1.branch_count <= 32
    assert plan1.refine_count <= 20
    assert "High success history" in plan1.reason


def test_policy_optimizer_monotonicity_guarantee(complex_tree: DiscoveryTree) -> None:
    trees = [complex_tree]
    optimizer = PolicyOptimizer()

    baseline = DynamicPortfolioPolicy(name="baseline", beta=0.2, worker_cap=3)
    candidate_a = DynamicPortfolioPolicy(name="candidate_exploit", beta=0.8, worker_cap=3)
    candidate_b = DynamicPortfolioPolicy(name="candidate_explore", beta=0.1, worker_cap=3)

    best_policy, comparison = optimizer.select_optimal_policy(
        candidate_policies=[candidate_a, candidate_b],
        baseline_policy=baseline,
        trees=trees,
        max_budget=20,
    )

    assert best_policy.name == comparison.selected_policy
    assert comparison.monotonicity_verified is True
    assert comparison.selected_replay_score >= comparison.baseline_replay_score
