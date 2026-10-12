import pytest
from pathlib import Path
from dream_rsi.core.models import DiscoveryTree, Observation, TreeNode
from dream_rsi.storage.store import JsonFileHistoryStore


def test_storage_save_load_tree(tmp_path: Path) -> None:
    store = JsonFileHistoryStore(base_dir=tmp_path)

    root = TreeNode(
        node_id="r1",
        observation=Observation(branch=0, attempt=0, score=0.4, evaluated=True),
    )
    tree = DiscoveryTree(tree_id="test_tree_01", root_id="r1")
    tree.add_node(root)

    saved_path = store.save_tree(tree)
    assert saved_path.exists()

    loaded = store.get_tree("test_tree_01")
    assert loaded is not None
    assert loaded.tree_id == "test_tree_01"
    assert loaded.root_id == "r1"
    assert len(loaded.nodes) == 1


def test_storage_save_node(tmp_path: Path) -> None:
    store = JsonFileHistoryStore(base_dir=tmp_path)
    root = TreeNode(
        node_id="r1",
        observation=Observation(branch=0, attempt=0, score=0.5, evaluated=True),
    )
    tree = DiscoveryTree(tree_id="tree_nodes", root_id="r1")
    tree.add_node(root)
    store.save_tree(tree)

    child = TreeNode(
        node_id="c1",
        parent_id="r1",
        branch_id=1,
        observation=Observation(branch=1, attempt=0, score=0.9, evaluated=True),
    )
    updated = store.save_node("tree_nodes", child)
    assert len(updated.nodes) == 2
    assert updated.get_best_score() == 0.9

    reloaded = store.get_tree("tree_nodes")
    assert reloaded is not None
    assert "c1" in reloaded.nodes


def test_storage_path_traversal_containment(tmp_path: Path) -> None:
    store = JsonFileHistoryStore(base_dir=tmp_path)

    with pytest.raises((PermissionError, ValueError)):
        store.get_tree("../../../windows/system32/cmd")


def test_storage_manifest(tmp_path: Path) -> None:
    store = JsonFileHistoryStore(base_dir=tmp_path)
    root = TreeNode(
        node_id="r1",
        observation=Observation(branch=0, attempt=0, score=0.5, evaluated=True),
    )
    tree1 = DiscoveryTree(tree_id="tree_a", root_id="r1")
    tree1.add_node(root)
    store.save_tree(tree1)

    manifest = store.get_manifest()
    assert manifest.total_trees == 1
    assert manifest.trees[0].tree_id == "tree_a"
    assert manifest.trees[0].best_score == 0.5


def test_storage_manifest_null_and_corrupt_resilience(tmp_path: Path) -> None:
    store = JsonFileHistoryStore(base_dir=tmp_path)

    bad_json = tmp_path / "corrupt_tree.json"
    bad_json.write_text("{not valid json", encoding="utf-8")

    null_fields_json = tmp_path / "null_tree.json"
    null_fields_json.write_text(
        '{"tree_id": "null_tree", "root_id": "r", "created_at": null, "nodes": {"r": {"observation": {"evaluated": true, "score": null}}}}',
        encoding="utf-8",
    )

    manifest = store.get_manifest()
    assert manifest.total_trees == 1
    assert manifest.trees[0].tree_id == "null_tree"
    assert manifest.trees[0].created_at == 0.0
    assert manifest.trees[0].best_score == 0.0


def test_storage_save_tree_indent_and_compact(tmp_path: Path) -> None:
    store = JsonFileHistoryStore(base_dir=tmp_path)
    root = TreeNode(
        node_id="r1",
        observation=Observation(branch=0, attempt=0, score=0.7, evaluated=True),
    )
    tree_indented = DiscoveryTree(tree_id="tree_indented", root_id="r1")
    tree_indented.add_node(root)
    path_ind = store.save_tree(tree_indented, indent=2)

    content_ind = path_ind.read_text(encoding="utf-8")
    assert "\n" in content_ind
    assert "  " in content_ind

    tree_compact = DiscoveryTree(tree_id="tree_compact", root_id="r1")
    tree_compact.add_node(root)
    path_cmp = store.save_tree(tree_compact, indent=None)

    content_cmp = path_cmp.read_text(encoding="utf-8")
    assert "\n" not in content_cmp
    assert len(content_cmp) < len(content_ind)

    loaded_ind = store.get_tree("tree_indented")
    loaded_cmp = store.get_tree("tree_compact")
    assert loaded_ind is not None
    assert loaded_cmp is not None
    assert loaded_ind.nodes == loaded_cmp.nodes
    assert loaded_ind.get_best_score() == loaded_cmp.get_best_score()
