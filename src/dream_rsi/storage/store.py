from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path

from dream_rsi.core.models import DiscoveryTree, StoreManifest, TreeManifestItem, TreeNode


class JsonFileHistoryStore:
    def __init__(self, base_dir: str | Path = "data/trees") -> None:
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_tree_id(self, tree_id: str) -> str:
        raw = str(tree_id).strip()
        if not raw:
            raise ValueError("Invalid empty tree_id.")
        if ".." in raw or "/" in raw or "\\" in raw:
            raise PermissionError(f"Path traversal detected: {tree_id}")
        return re.sub(r"[^a-zA-Z0-9_\-]", "_", raw)

    def _resolve_tree_path(self, tree_id: str) -> Path:
        clean_id = self._sanitize_tree_id(tree_id)
        target = (self.base_dir / f"{clean_id}.json").resolve()
        if not str(target).startswith(str(self.base_dir)):
            raise PermissionError(f"Path traversal detected: {tree_id}")
        return target

    def save_tree(self, tree: DiscoveryTree, *, indent: int | None = 2) -> Path:
        tree.check_integrity()
        target_path = self._resolve_tree_path(tree.tree_id)
        temp_path = self.base_dir / f".tmp_{uuid.uuid4().hex}.json"

        encoded = tree.model_dump_json(indent=indent)

        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(encoded)
            f.flush()
            os.fsync(f.fileno())

        os.replace(temp_path, target_path)
        return target_path

    def get_tree(self, tree_id: str) -> DiscoveryTree | None:
        target_path = self._resolve_tree_path(tree_id)
        if not target_path.exists() or not target_path.is_file():
            return None

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data: object = json.load(f)
            return DiscoveryTree.model_validate(data)
        except (json.JSONDecodeError, ValueError, OSError):
            return None

    def list_trees(self) -> list[str]:
        trees: list[str] = []
        for file in sorted(self.base_dir.glob("*.json")):
            if not file.name.startswith(".tmp_"):
                trees.append(file.stem)
        return trees

    def save_node(self, tree_id: str, node: TreeNode) -> DiscoveryTree:
        tree = self.get_tree(tree_id)
        if tree is None:
            raise KeyError(f"Tree '{tree_id}' does not exist.")
        tree.add_node(node)
        self.save_tree(tree)
        return tree

    def delete_tree(self, tree_id: str) -> bool:
        target_path = self._resolve_tree_path(tree_id)
        if target_path.exists():
            target_path.unlink()
            return True
        return False

    def get_manifest(self) -> StoreManifest:
        manifest_entries: list[TreeManifestItem] = []
        for tid in self.list_trees():
            target_path = self._resolve_tree_path(tid)
            if not target_path.exists() or not target_path.is_file():
                continue
            try:
                with open(target_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    continue
                nodes_raw = data.get("nodes", {})
                branches_raw = data.get("branches", {})
                node_count = len(nodes_raw) if isinstance(nodes_raw, dict) else 0
                branch_count = len(branches_raw) if isinstance(branches_raw, dict) else 0
                best_score = 0.0
                if isinstance(nodes_raw, dict):
                    for n_data in nodes_raw.values():
                        if isinstance(n_data, dict):
                            obs = n_data.get("observation", {})
                            if isinstance(obs, dict) and obs.get("evaluated", False):
                                s_val = obs.get("score")
                                s = float(s_val) if isinstance(s_val, (int, float)) else 0.0
                                if s > best_score:
                                    best_score = s
                meta_raw = data.get("metadata", {})
                metadata = meta_raw if isinstance(meta_raw, dict) else {}
                c_val = data.get("created_at")
                created_at = float(c_val) if isinstance(c_val, (int, float)) else 0.0
                manifest_entries.append(
                    TreeManifestItem(
                        tree_id=str(data.get("tree_id", tid)),
                        root_id=str(data.get("root_id", "")),
                        node_count=node_count,
                        branch_count=branch_count,
                        best_score=best_score,
                        created_at=created_at,
                        metadata=metadata,
                    )
                )
            except Exception:
                tree = self.get_tree(tid)
                if tree is not None:
                    manifest_entries.append(
                        TreeManifestItem(
                            tree_id=tree.tree_id,
                            root_id=tree.root_id,
                            node_count=len(tree.nodes),
                            branch_count=len(tree.branches),
                            best_score=tree.get_best_score(),
                            created_at=tree.created_at,
                            metadata=tree.metadata,
                        )
                    )
        return StoreManifest(
            total_trees=len(manifest_entries),
            base_dir=str(self.base_dir),
            trees=manifest_entries,
        )
