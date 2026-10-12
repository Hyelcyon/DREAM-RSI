import pytest
from pathlib import Path
from dream_rsi.core.models import DiscoveryTree, Observation, TreeNode
from dream_rsi.replay.question import QuestionAPI
from dream_rsi.core.evaluator import ReplayEvaluator
from dream_rsi.storage.store import JsonFileHistoryStore


def test_question_api_leaf_and_admissible_topological_invariants():
    """Verify that QuestionAPI leaves strictly satisfy topological invariants at every probe step."""
    root = TreeNode(
        node_id="root",
        observation=Observation(branch=0, attempt=0, score=0.1, evaluated=True),
    )
    tree = DiscoveryTree(tree_id="inv_tree", root_id="root")
    tree.add_node(root)

    # Build 3 branches of depth 3
    for b in range(1, 4):
        prev_id = "root"
        for d in range(1, 4):
            nid = f"b{b}_d{d}"
            node = TreeNode(
                node_id=nid,
                parent_id=prev_id,
                branch_id=b,
                attempt_index=d - 1,
                depth=d,
                observation=Observation(branch=b, attempt=d - 1, score=0.1 * (b + d), evaluated=True),
            )
            tree.add_node(node)
            prev_id = nid

    q = QuestionAPI(tree, max_parallelism=5, max_budget=20)

    # Invariant at start
    assert set(q.get_leaves_of_observed()) == {"root"}
    assert q.admissible_continuations() == {"root"}

    # Probe 2 branches from root
    q.probe_batch(["root", "root"])
    observed = q.observed()
    assert "root" not in q.get_leaves_of_observed()
    assert set(q.get_leaves_of_observed()) == {"b1_d1", "b2_d1"}
    assert q.admissible_continuations() == {"root", "b1_d1", "b2_d1"}

    # Invariant: No leaf has children in observed
    for leaf in q.get_leaves_of_observed():
        assert not any(n.parent_id == leaf for n in observed.values())

    # Probe b1_d1 to reveal b1_d2
    q.probe_batch(["b1_d1"])
    observed = q.observed()
    assert "b1_d1" not in q.get_leaves_of_observed()
    assert set(q.get_leaves_of_observed()) == {"b1_d2", "b2_d1"}
    assert q.admissible_continuations() == {"root", "b1_d2", "b2_d1"}

    for leaf in q.get_leaves_of_observed():
        assert not any(n.parent_id == leaf for n in observed.values())


def test_tree_cycle_detection_invariants():
    """Test cycle detection across various cyclic structures."""
    root = TreeNode(node_id="r", observation=Observation(branch=0, attempt=0, score=0.1, evaluated=True))

    # Long cycle: r -> 1 -> 2 -> 3 -> 4 -> 5 -> 1
    nodes: dict[str, TreeNode] = {"r": root}
    for i in range(1, 6):
        nodes[str(i)] = TreeNode(
            node_id=str(i),
            parent_id="r" if i == 1 else str(i - 1),
            observation=Observation(branch=1, attempt=i, score=0.1, evaluated=True),
        )
    # create loop 5 -> 1
    nodes["1"] = TreeNode(
        node_id="1",
        parent_id="5",
        observation=Observation(branch=1, attempt=1, score=0.1, evaluated=True),
    )

    with pytest.raises(ValueError, match="Cycle detected"):
        DiscoveryTree(tree_id="long_cycle", root_id="r", nodes=nodes)


def test_evaluator_pareto_auc_mathematical_bounds():
    """Test that Pareto AUC strictly obeys mathematical bounds [0, max_score]."""
    evaluator = ReplayEvaluator()

    for budget in [1, 5, 10, 50]:
        # Constant score trajectory starting from probe 0
        curve = [(0, 0.75)]
        auc = evaluator.calculate_pareto_auc(curve, max_budget=budget)
        assert pytest.approx(auc, rel=1e-5) == 0.75

        # Increasing score trajectory
        inc_curve = [(0, 0.0)] + [(p, p / budget) for p in range(1, budget + 1)]
        inc_auc = evaluator.calculate_pareto_auc(inc_curve, max_budget=budget)
        assert 0.0 <= inc_auc <= 1.0


def test_store_atomic_write_and_corruption_isolation(tmp_path: Path):
    """Test that store writes atomically and safely ignores corrupt and unparseable files."""
    store = JsonFileHistoryStore(base_dir=tmp_path)
    root = TreeNode(node_id="r", observation=Observation(branch=0, attempt=0, score=0.5, evaluated=True))
    tree = DiscoveryTree(tree_id="good_tree", root_id="r")
    tree.add_node(root)
    store.save_tree(tree)

    # Inject garbage file and null-field file
    (tmp_path / "broken.json").write_text("{broken", encoding="utf-8")
    (tmp_path / "empty.json").write_text("", encoding="utf-8")

    manifest = store.get_manifest()
    assert manifest.total_trees == 1
    assert manifest.trees[0].tree_id == "good_tree"

    assert store.get_tree("broken") is None
    assert store.get_tree("empty") is None
