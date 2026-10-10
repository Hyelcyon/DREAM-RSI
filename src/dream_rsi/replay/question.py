from __future__ import annotations

import math
from dream_rsi.core.models import DiscoveryTree, TreeNode

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

        root_node = tree.nodes[tree.root_id]
        self._observed: dict[str, TreeNode] = {tree.root_id: root_node.model_copy(deep=True)}
        self._revealed_node_ids: list[str] = [tree.root_id]
        self._probes_spent: int = 0
        self._rounds_spent: int = 0
        self._effective_sequential_rounds: float = 0.0

        initial_score = root_node.observation.score if root_node.observation.evaluated else 0.0
        self._current_best_score: float = initial_score
        self._trajectory: list[tuple[int, float]] = [(0, self._current_best_score)]

    @property
    def max_parallelism(self) -> int:
        return self._max_parallelism

    @property
    def max_budget(self) -> int:
        return self._max_budget

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
        return {nid: node.model_copy(deep=True) for nid, node in self._observed.items()}

    def get_leaves_of_observed(self) -> list[str]:
        all_parents = {
            node.parent_id
            for node in self._observed.values()
            if node.parent_id is not None
        }
        return [
            nid for nid in self._observed.keys()
            if nid not in all_parents
        ]

    def admissible_continuations(self) -> set[str]:
        leaves = set(self.get_leaves_of_observed())
        return {self._tree.root_id} | leaves

    def get_unrevealed_continuations(self) -> set[str]:
        candidates: set[str] = set()
        for cand_id in self.admissible_continuations():
            unrevealed = self._find_unrevealed_children(cand_id)
            if unrevealed:
                candidates.add(cand_id)
        return candidates

    def _find_unrevealed_children(self, parent_id: str) -> list[str]:
        unrevealed: list[str] = []
        for nid, node in self._tree.nodes.items():
            if node.parent_id == parent_id and nid not in self._observed:
                unrevealed.append(nid)
        unrevealed.sort(key=lambda x: (self._tree.nodes[x].created_at, self._tree.nodes[x].attempt_index))
        return unrevealed

    def _is_ancestor_in_observed(self, ancestor_id: str, descendant_id: str) -> bool:
        current = self._observed.get(descendant_id)
        while current is not None and current.parent_id is not None:
            if current.parent_id == ancestor_id:
                return True
            current = self._observed.get(current.parent_id)
        return False

    def probe_batch(self, parent_ids: list[str]) -> list[TreeNode]:
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
                revealed_node = self._tree.nodes[target_id].model_copy(deep=True)
                self._observed[target_id] = revealed_node
                self._revealed_node_ids.append(target_id)
                newly_revealed_nodes.append(revealed_node)

                if revealed_node.observation.evaluated:
                    if revealed_node.observation.score > self._current_best_score:
                        self._current_best_score = revealed_node.observation.score

        probes_cost = len(active_batch)
        self._probes_spent += probes_cost
        self._rounds_spent += 1
        self._effective_sequential_rounds += math.ceil(probes_cost / self._max_parallelism)
        self._trajectory.append((self._probes_spent, self._current_best_score))

        return newly_revealed_nodes
