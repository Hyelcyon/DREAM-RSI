import pytest
from dream_rsi.core.models import (
    DiscoveryTree,
    Observation,
    TreeNode,
)


def test_observation_success_and_repairable_contract():
    obs_ok = Observation(
        branch=1,
        attempt=0,
        score=0.85,
        evaluated=True,
        valid=False,
        fail_class="ok",
        error=None,
    )
    assert obs_ok.is_successful is True
    assert obs_ok.is_repairable is False

    obs_err = Observation(
        branch=1,
        attempt=1,
        score=0.0,
        evaluated=True,
        valid=False,
        fail_class="compile_error",
        error="SyntaxError: invalid syntax",
    )
    assert obs_err.is_successful is False
    assert obs_err.is_repairable is True

    obs_fatal = Observation(
        branch=1,
        attempt=2,
        score=0.0,
        evaluated=True,
        valid=False,
        fail_class="algorithm_diverged",
        error="Fatal divergence",
    )
    assert obs_fatal.is_successful is False
    assert obs_fatal.is_repairable is False


def test_tree_cycle_detection():
    root = TreeNode(
        node_id="root",
        observation=Observation(branch=0, attempt=0, score=0.1, evaluated=True),
    )
    node_a = TreeNode(
        node_id="a",
        parent_id="b",
        observation=Observation(branch=1, attempt=0, score=0.2, evaluated=True),
    )
    node_b = TreeNode(
        node_id="b",
        parent_id="a",
        observation=Observation(branch=1, attempt=1, score=0.3, evaluated=True),
    )

    with pytest.raises(ValueError, match="Cycle detected"):
        DiscoveryTree(
            tree_id="cycle_tree",
            root_id="root",
            nodes={"root": root, "a": node_a, "b": node_b},
        )

    node_self = TreeNode(
        node_id="self_loop",
        parent_id="self_loop",
        observation=Observation(branch=1, attempt=0, score=0.1, evaluated=True),
    )
    with pytest.raises(ValueError, match="Cycle detected"):
        DiscoveryTree(
            tree_id="self_loop_tree",
            root_id="root",
            nodes={"root": root, "self_loop": node_self},
        )

    node_c1 = TreeNode(node_id="c1", parent_id="c2", observation=Observation(branch=1, attempt=0, score=0.1, evaluated=True))
    node_c2 = TreeNode(node_id="c2", parent_id="c3", observation=Observation(branch=1, attempt=1, score=0.1, evaluated=True))
    node_c3 = TreeNode(node_id="c3", parent_id="c1", observation=Observation(branch=1, attempt=2, score=0.1, evaluated=True))
    with pytest.raises(ValueError, match="Cycle detected"):
        DiscoveryTree(
            tree_id="tri_cycle_tree",
            root_id="root",
            nodes={"root": root, "c1": node_c1, "c2": node_c2, "c3": node_c3},
        )


def test_tree_missing_parent_validation():
    root = TreeNode(
        node_id="root",
        observation=Observation(branch=0, attempt=0, score=0.1, evaluated=True),
    )
    child = TreeNode(
        node_id="c1",
        parent_id="missing_p",
        observation=Observation(branch=1, attempt=0, score=0.2, evaluated=True),
    )

    with pytest.raises(ValueError, match="Parent 'missing_p' of node 'c1' does not exist"):
        DiscoveryTree(
            tree_id="bad_tree",
            root_id="root",
            nodes={"root": root, "c1": child},
        )


def test_tree_leaves_and_continuations():
    root = TreeNode(
        node_id="r",
        observation=Observation(branch=0, attempt=0, score=0.5, evaluated=True),
    )
    tree = DiscoveryTree(tree_id="t1", root_id="r")
    tree.add_node(root)

    assert [n.node_id for n in tree.get_leaves()] == ["r"]
    assert tree.get_admissible_continuations() == {"r"}

    c1 = TreeNode(
        node_id="c1",
        parent_id="r",
        branch_id=1,
        observation=Observation(branch=1, attempt=0, score=0.8, evaluated=True),
    )
    tree.add_node(c1)

    leaves = {n.node_id for n in tree.get_leaves()}
    assert leaves == {"c1"}
    assert tree.get_admissible_continuations() == {"r", "c1"}
    assert tree.get_best_score() == 0.8


def test_tree_leaf_cache_invalidation_and_immutability():
    root = TreeNode(node_id="r", observation=Observation(branch=0, attempt=0, score=0.5, evaluated=True))
    tree = DiscoveryTree(tree_id="cache_test", root_id="r")
    tree.add_node(root)

    leaves_first = tree.get_leaves()
    assert len(leaves_first) == 1
    leaves_first.clear()
    assert len(tree.get_leaves()) == 1

    c1 = TreeNode(node_id="c1", parent_id="r", branch_id=1, observation=Observation(branch=1, attempt=0, score=0.6, evaluated=True))
    tree.add_node(c1)
    assert [n.node_id for n in tree.get_leaves()] == ["c1"]
    assert tree.get_admissible_continuations() == {"r", "c1"}

    c2 = TreeNode(node_id="c2", parent_id="c1", branch_id=1, observation=Observation(branch=1, attempt=1, score=0.7, evaluated=True))
    tree.add_node(c2)
    assert [n.node_id for n in tree.get_leaves()] == ["c2"]
    assert tree.get_admissible_continuations() == {"r", "c2"}
