from __future__ import annotations

import time
from pydantic import BaseModel, Field, model_validator

JsonScalar = str | int | float | bool | None
JsonPrimitiveDict = dict[str, str | int | float | bool]

class Observation(BaseModel):
    branch: int
    attempt: int
    score: float = 0.0
    evaluated: bool = False
    valid: bool = False
    fail_class: str = "ok"
    error: str | None = None
    delta_vs_baseline: float = 0.0
    delta_vs_parent: float = 0.0
    n_valid: int = 0
    n_total: int = 0
    metadata: JsonPrimitiveDict = Field(default_factory=dict)

    @property
    def is_successful(self) -> bool:
        return self.evaluated and (self.error is None) and (self.fail_class == "ok")

    @property
    def is_repairable(self) -> bool:
        if self.is_successful:
            return False
        repairable_classes = {
            "compile_error",
            "shape_mismatch",
            "runtime_error",
            "resource_limit",
            "timeout",
            "syntax_error",
            "compile_other",
            "output_mismatch",
            "correctness_mismatch",
            "code_error",
            "memory_limit",
        }
        return self.fail_class in repairable_classes


class CellMeta(BaseModel):
    cell_id: str
    branch: int
    attempt: int
    parent_id: str | None = None
    seq: int = 0
    tags: JsonPrimitiveDict = Field(default_factory=dict)


class TreeNode(BaseModel):
    node_id: str
    parent_id: str | None = None
    branch_id: int = 0
    attempt_index: int = 0
    depth: int = 0
    workspace_state: JsonPrimitiveDict = Field(default_factory=dict)
    artifact_code: str = ""
    observation: Observation
    created_at: float = Field(default_factory=time.time)

    @property
    def is_root(self) -> bool:
        return self.parent_id is None

    @property
    def branch(self) -> int:
        return self.observation.branch

    @property
    def attempt(self) -> int:
        return self.observation.attempt

    @property
    def score(self) -> float:
        return self.observation.score

    @property
    def evaluated(self) -> bool:
        return self.observation.evaluated

    @property
    def valid(self) -> bool:
        return self.observation.valid

    @property
    def fail_class(self) -> str:
        return self.observation.fail_class

    @property
    def error(self) -> str | None:
        return self.observation.error

    @property
    def delta_vs_baseline(self) -> float:
        return self.observation.delta_vs_baseline

    @property
    def delta_vs_parent(self) -> float:
        return self.observation.delta_vs_parent

    @property
    def n_valid(self) -> int:
        return self.observation.n_valid

    @property
    def n_total(self) -> int:
        return self.observation.n_total

    @property
    def is_successful(self) -> bool:
        return self.observation.is_successful

    @property
    def is_repairable(self) -> bool:
        return self.observation.is_repairable


def _default_branches() -> dict[int, list[str]]:
    return {}


def _default_nodes() -> dict[str, TreeNode]:
    return {}


def _default_metadata() -> JsonPrimitiveDict:
    return {}


class DiscoveryTree(BaseModel):
    tree_id: str
    root_id: str
    nodes: dict[str, TreeNode] = Field(default_factory=_default_nodes)
    branches: dict[int, list[str]] = Field(default_factory=_default_branches)
    created_at: float = Field(default_factory=time.time)
    metadata: JsonPrimitiveDict = Field(default_factory=_default_metadata)

    def check_integrity(self) -> None:
        if self.root_id and self.nodes and self.root_id not in self.nodes:
            raise ValueError(f"Root node '{self.root_id}' must exist in nodes.")

        for node_id, node in self.nodes.items():
            if node.is_root:
                continue
            if node.parent_id not in self.nodes:
                raise ValueError(f"Parent '{node.parent_id}' of node '{node_id}' does not exist.")

            current = node.parent_id
            seen_ancestors: set[str] = {node_id}
            while current is not None:
                if current in seen_ancestors:
                    raise ValueError(f"Cycle detected in discovery tree at node '{current}'.")
                seen_ancestors.add(current)
                current = self.nodes[current].parent_id

    @model_validator(mode="after")
    def _validate_tree_integrity(self) -> DiscoveryTree:
        self.check_integrity()
        return self

    def add_node(self, node: TreeNode) -> None:
        if not node.is_root and node.parent_id not in self.nodes:
            raise ValueError(f"Parent '{node.parent_id}' must exist in tree before adding child.")

        self.nodes[node.node_id] = node
        if node.branch_id not in self.branches:
            self.branches[node.branch_id] = []
        if node.node_id not in self.branches[node.branch_id]:
            self.branches[node.branch_id].append(node.node_id)

    def get_leaves(self) -> list[TreeNode]:
        all_parent_ids = {node.parent_id for node in self.nodes.values() if node.parent_id is not None}
        return [node for node_id, node in self.nodes.items() if node_id not in all_parent_ids]

    def get_admissible_continuations(self) -> set[str]:
        leaves = {node.node_id for node in self.get_leaves()}
        return {self.root_id} | leaves

    def get_branch_history(self, branch_id: int) -> list[TreeNode]:
        node_ids = self.branches.get(branch_id, [])
        return [self.nodes[nid] for nid in node_ids if nid in self.nodes]

    def get_best_score(self) -> float:
        scores = [node.observation.score for node in self.nodes.values() if node.observation.evaluated]
        return max(scores) if scores else 0.0


class GridPlan(BaseModel):
    branch_count: int = Field(ge=1, description="Width W: branches 0..W-1")
    refine_count: int = Field(ge=0, description="Depth R: refinements allowed after each root")
    reason: str = Field(description="Factual evidence-based rationale")


class HistorySummaryItem(BaseModel):
    tree_id: str
    best_score: float = 0.0
    max_depth: int = 0
    node_count: int = 0
    early_improvements: int = 0
    stalled_deep_refinements: int = 0
    late_high_gains: int = 0
    plateaued_branches: int = 0
    hard_failures: int = 0


def _default_history() -> list[HistorySummaryItem]:
    return []


class GridPlanningContext(BaseModel):
    history: list[HistorySummaryItem] = Field(default_factory=_default_history)
    hard_max_branch_count: int = Field(default=32, ge=1)
    hard_max_refine_count: int = Field(default=20, ge=0)
    worker_cap: int = Field(default=10, ge=1)
    trace_branch_count: int | None = None
    trace_refine_count: int | None = None


def _default_str_list() -> list[str]:
    return []


def _default_str_float_dict() -> dict[str, float]:
    return {}


class ReplayEvaluationResult(BaseModel):
    policy_name: str
    beta: float
    max_score: float
    total_probes: int
    decision_rounds: int
    effective_sequential_rounds: float
    replay_score: float
    pareto_auc: float = 0.0
    parallel_penalty: float = 0.0
    pareto_reward: float = 0.0
    revealed_node_ids: list[str] = Field(default_factory=_default_str_list)
    trajectory_summary: dict[str, float] = Field(default_factory=_default_str_float_dict)


class TreeManifestItem(BaseModel):
    tree_id: str
    root_id: str
    node_count: int
    branch_count: int
    best_score: float
    created_at: float
    metadata: JsonPrimitiveDict = Field(default_factory=_default_metadata)


class StoreManifest(BaseModel):
    total_trees: int
    base_dir: str
    trees: list[TreeManifestItem]
