import pytest
from dream_rsi.core.models import DiscoveryTree, Observation, TreeNode
from dream_rsi.replay.question import QuestionAPI


@pytest.fixture
def sample_tree() -> DiscoveryTree:
    root = TreeNode(
        node_id="root",
        observation=Observation(branch=0, attempt=0, score=0.2, evaluated=True),
    )
    b1_n1 = TreeNode(
        node_id="b1_n1",
        parent_id="root",
        branch_id=1,
        attempt_index=0,
        observation=Observation(branch=1, attempt=0, score=0.5, evaluated=True),
    )
    b1_n2 = TreeNode(
        node_id="b1_n2",
        parent_id="b1_n1",
        branch_id=1,
        attempt_index=1,
        observation=Observation(branch=1, attempt=1, score=0.8, evaluated=True),
    )
    b2_n1 = TreeNode(
        node_id="b2_n1",
        parent_id="root",
        branch_id=2,
        attempt_index=0,
        observation=Observation(
            branch=2,
            attempt=0,
            score=0.1,
            evaluated=True,
            fail_class="compile_error",
            error="gcc error",
        ),
    )

    tree = DiscoveryTree(tree_id="t_sample", root_id="root")
    tree.add_node(root)
    tree.add_node(b1_n1)
    tree.add_node(b1_n2)
    tree.add_node(b2_n1)
    return tree


def test_question_api_initial_prefix_isolation(sample_tree: DiscoveryTree):
    q = QuestionAPI(sample_tree, max_parallelism=5, max_budget=20)

    observed = q.observed()
    assert list(observed.keys()) == ["root"]
    assert "b1_n1" not in observed
    assert "b1_n2" not in observed

    assert q.admissible_continuations() == {"root"}


def test_question_api_probe_and_reveal(sample_tree: DiscoveryTree):
    q = QuestionAPI(sample_tree, max_parallelism=5, max_budget=20)

    revealed = q.probe_batch(["root", "root"])
    assert len(revealed) == 2
    revealed_ids = {n.node_id for n in revealed}
    assert revealed_ids == {"b1_n1", "b2_n1"}

    obs = q.observed()
    assert set(obs.keys()) == {"root", "b1_n1", "b2_n1"}
    assert "b1_n2" not in obs

    admissible = q.admissible_continuations()
    assert admissible == {"root", "b1_n1", "b2_n1"}
    assert set(q.get_leaves_of_observed()) == {"b1_n1", "b2_n1"}

    revealed_2 = q.probe_batch(["b1_n1"])
    assert len(revealed_2) == 1
    assert revealed_2[0].node_id == "b1_n2"
    assert q.observed()["b1_n2"].observation.score == 0.8
    assert set(q.get_leaves_of_observed()) == {"b2_n1", "b1_n2"}
    assert q.admissible_continuations() == {"root", "b2_n1", "b1_n2"}


def test_question_api_batch_parallelism_limit(sample_tree: DiscoveryTree):
    q = QuestionAPI(sample_tree, max_parallelism=2, max_budget=20)

    with pytest.raises(ValueError, match="Batch size 3 exceeds maximum parallelism W=2"):
        q.probe_batch(["root", "root", "root"])


def test_question_api_parent_child_co_occurrence_violation(sample_tree: DiscoveryTree):
    q = QuestionAPI(sample_tree, max_parallelism=5, max_budget=20)

    q.probe_batch(["root"])

    with pytest.raises(ValueError, match="Parent-child co-occurrence violation"):
        q.probe_batch(["root", "b1_n1"])


def test_question_api_non_admissible_rejection(sample_tree: DiscoveryTree):
    q = QuestionAPI(sample_tree, max_parallelism=5, max_budget=20)

    with pytest.raises(ValueError, match="is not in admissible continuation set"):
        q.probe_batch(["unseen_future_node"])


def test_question_api_budget_exhaustion(sample_tree: DiscoveryTree):
    q = QuestionAPI(sample_tree, max_parallelism=5, max_budget=2)

    q.probe_batch(["root", "root"])
    assert q.probes_spent == 2
    assert q.is_exhausted() is True

    res = q.probe_batch(["b1_n1"])
    assert res == []
