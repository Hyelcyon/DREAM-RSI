from __future__ import annotations

import math
from typing import Callable
from dream_rsi.core.models import CellMeta, DiscoveryTree, TreeNode


class QuestionAPI:
    def __init__(
        self,
        tree: DiscoveryTree,
        max_parallelism: int = 10,
        max_budget: int = 100,
    ) -> None:
        self._tree: DiscoveryTree = tree
        self._max_parallelism: int = max(1, int(max_parallelism))
        self._max_budget: int = max(1, int(max_budget))

        if tree.root_id not in tree.nodes:
            raise ValueError(f"Root node '{tree.root_id}' missing in tree.")

        self._children_by_parent: dict[str, list[str]] = {}
        for nid, node in tree.nodes.items():
            pid = node.parent_id
            if pid is not None:
                if pid not in self._children_by_parent:
                    self._children_by_parent[pid] = []
                self._children_by_parent[pid].append(nid)

        for child_list in self._children_by_parent.values():
            child_list.sort(key=lambda x: (tree.nodes[x].created_at, tree.nodes[x].attempt_index))

        self._baseline_score: float = float(tree.metadata.get("baseline_score", 0.0))
        self._observed: dict[str, TreeNode] = {}
        self._revealed_node_ids: list[str] = []
        self._probes_spent: int = 0
        self._rounds_spent: int = 0
        self._effective_sequential_rounds: float = 0.0
        self._current_best_score: float = 0.0
        self._trajectory: list[tuple[int, float]] = []
        self._leaves: set[str] = set()

        self.reset()

    def reset(self) -> None:
        """Resets the exploration state to the root observation."""
        root_node = self._tree.nodes[self._tree.root_id]
        self._observed = {self._tree.root_id: root_node}
        self._revealed_node_ids = [self._tree.root_id]
        self._leaves = {self._tree.root_id}
        self._probes_spent = 0
        self._rounds_spent = 0
        self._effective_sequential_rounds = 0.0

        initial_score = root_node.observation.score if root_node.observation.evaluated else 0.0
        self._current_best_score = initial_score
        self._trajectory = [(0, self._current_best_score)]

    @property
    def max_parallelism(self) -> int:
        return self._max_parallelism

    @property
    def max_budget(self) -> int:
        return self._max_budget

    @property
    def baseline_score(self) -> float:
        return self._baseline_score

    @property
    def probes_spent(self) -> int:
        return self._probes_spent

    @property
    def rounds_spent(self) -> int:
        return self._rounds_spent

    @property
    def effective_sequential_rounds(self) -> float:
        return self._effective_sequential_rounds

    @property
    def trajectory(self) -> list[tuple[int, float]]:
        return list(self._trajectory)

    @property
    def revealed_node_ids(self) -> list[str]:
        return list(self._revealed_node_ids)

    def is_exhausted(self) -> bool:
        if self._probes_spent >= self._max_budget:
            return True
        return len(self.get_unrevealed_continuations()) == 0

    def observed(self) -> dict[str, TreeNode]:
        return dict(self._observed)

    def get_leaves_of_observed(self) -> list[str]:
        return [nid for nid in self._observed.keys() if nid in self._leaves]

    def admissible_continuations(self) -> set[str]:
        return set(self._leaves) | {self._tree.root_id}

    def legal_actions(self) -> list[str]:
        """Returns valid continuations that have unrevealed candidate children."""
        unrevealed = self.get_unrevealed_continuations()
        return sorted(list(unrevealed))

    def legal_roots(self) -> list[str]:
        """Returns root continuations if unrevealed branches remain available."""
        if self._find_unrevealed_children(self._tree.root_id):
            return [self._tree.root_id]
        return []

    def opened_branches(self) -> list[int]:
        """Returns sorted list of distinct branch IDs observed so far."""
        branches: set[int] = {
            node.branch_id
            for node in self._observed.values()
            if not node.is_root
        }
        return sorted(list(branches))

    def meta(self, cell_id: str) -> CellMeta:
        """Returns metadata structure for a given cell ID."""
        node = self._tree.nodes.get(cell_id)
        if node is None:
            raise KeyError(f"Cell ID '{cell_id}' not found in discovery tree.")
        return CellMeta(
            cell_id=node.node_id,
            branch=node.branch_id,
            attempt=node.attempt_index,
            parent_id=node.parent_id,
            seq=node.depth,
            tags={"is_root": node.is_root, "depth": node.depth},
        )

    def get_unrevealed_continuations(self) -> set[str]:
        candidates: set[str] = set()
        for cand_id in self.admissible_continuations():
            unrevealed = self._find_unrevealed_children(cand_id)
            if unrevealed:
                candidates.add(cand_id)
        return candidates

    def _find_unrevealed_children(self, parent_id: str) -> list[str]:
        children = self._children_by_parent.get(parent_id, [])
        return [cid for cid in children if cid not in self._observed]

    def _is_ancestor_in_observed(self, ancestor_id: str, descendant_id: str) -> bool:
        current = self._observed.get(descendant_id)
        while current is not None and current.parent_id is not None:
            if current.parent_id == ancestor_id:
                return True
            current = self._observed.get(current.parent_id)
        return False

    def probe_batch(
        self,
        parent_ids: list[str],
        on_reveal: Callable[[TreeNode], None] | None = None,
    ) -> list[TreeNode]:
        if self.is_exhausted():
            return []

        if not parent_ids:
            return []

        if len(parent_ids) > self._max_parallelism:
            raise ValueError(
                f"Batch size {len(parent_ids)} exceeds maximum parallelism W={self._max_parallelism}."
            )

        admissible = self.admissible_continuations()
        for pid in parent_ids:
            if pid not in admissible:
                raise ValueError(
                    f"Candidate parent '{pid}' is not in admissible continuation set A(T_k)."
                )

        for i, u in enumerate(parent_ids):
            for j, v in enumerate(parent_ids):
                if i != j and self._is_ancestor_in_observed(u, v):
                    raise ValueError(
                        f"Parent-child co-occurrence violation: '{u}' is ancestor of '{v}' in the same batch."
                    )

        non_root_parents = [p for p in parent_ids if p != self._tree.root_id]
        if len(non_root_parents) != len(set(non_root_parents)):
            raise ValueError("Duplicate non-root parent in the same batch.")

        remaining_budget = self._max_budget - self._probes_spent
        active_batch = parent_ids[:remaining_budget]
        if not active_batch:
            return []

        newly_revealed_nodes: list[TreeNode] = []
        claimed_node_ids: set[str] = set()

        for pid in active_batch:
            unrevealed = self._find_unrevealed_children(pid)
            eligible = [nid for nid in unrevealed if nid not in claimed_node_ids]
            if eligible:
                target_id = eligible[0]
                claimed_node_ids.add(target_id)
                revealed_node = self._tree.nodes[target_id]
                self._observed[target_id] = revealed_node
                self._revealed_node_ids.append(target_id)
                self._leaves.add(target_id)
                if revealed_node.parent_id is not None:
                    self._leaves.discard(revealed_node.parent_id)
                newly_revealed_nodes.append(revealed_node)

                if revealed_node.observation.evaluated:
                    if revealed_node.observation.score > self._current_best_score:
                        self._current_best_score = revealed_node.observation.score

                if on_reveal is not None:
                    on_reveal(revealed_node)

        probes_cost = len(active_batch)
        self._probes_spent += probes_cost
        self._rounds_spent += 1
        self._effective_sequential_rounds += math.ceil(probes_cost / self._max_parallelism)
        self._trajectory.append((self._probes_spent, self._current_best_score))

        return newly_revealed_nodes
