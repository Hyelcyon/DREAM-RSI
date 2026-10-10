from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

from dream_rsi.core.models import Observation, TreeNode

FailureClass = Literal[
    "ok",
    "compile_error",
    "shape_mismatch",
    "runtime_error",
    "resource_limit",
    "timeout",
    "syntax_error",
    "compile_other",
    "environment_failure",
    "dependency_failure",
    "unknown",
]


def branch_promising(obs: Observation, min_gain: float = 0.0) -> bool:
    """Returns True if observation demonstrated positive gain vs parent or baseline."""
    if not obs.is_successful:
        return False
    return (obs.delta_vs_parent > min_gain) or (obs.delta_vs_baseline > min_gain)


def branch_failed_hard(obs: Observation) -> bool:
    """Returns True if the failure is unrecoverable (e.g. environment/dependency issues)."""
    if obs.is_successful:
        return False
    hard_failure_classes = {
        "environment_failure",
        "dependency_failure",
        "missing_driver",
        "unsupported_arch",
    }
    if obs.fail_class in hard_failure_classes:
        return True
    if obs.error is not None:
        lowered = obs.error.lower()
        if "no cuda-capable device" in lowered or "segmentation fault (core dumped)" in lowered:
            return True
    return False


def probe_improved_vs_parent(obs: Observation) -> bool:
    """Returns True if score strictly improved over the parent node."""
    return obs.is_successful and (obs.delta_vs_parent > 0.0)


def probe_improved_vs_baseline(obs: Observation) -> bool:
    """Returns True if score strictly improved over the task baseline."""
    return obs.is_successful and (obs.delta_vs_baseline > 0.0)


class BranchTrajectory(BaseModel):
    branch_id: int
    node_ids: list[str] = Field(default_factory=list)
    scores: list[float] = Field(default_factory=list)
    best_score: float = 0.0
    successful_anchor_score: float = 0.0
    has_successful_anchor: bool = False
    consecutive_failures: int = 0
    total_failures: int = 0
    total_attempts: int = 0
    is_closed: bool = False
    closure_reason: str | None = None

    @classmethod
    def from_nodes(cls, branch_id: int, nodes: list[TreeNode]) -> BranchTrajectory:
        traj = cls(branch_id=branch_id)
        for node in nodes:
            traj.add_node(node)
        return traj

    def add_node(self, node: TreeNode) -> None:
        self.node_ids.append(node.node_id)
        obs = node.observation
        score = obs.score if obs.evaluated else 0.0
        self.scores.append(score)
        self.total_attempts += 1

        if score > self.best_score:
            self.best_score = score

        if obs.is_successful:
            self.has_successful_anchor = True
            if score > self.successful_anchor_score:
                self.successful_anchor_score = score
            self.consecutive_failures = 0
            if self.is_closed and self.closure_reason != "hard_unrecoverable":
                self.is_closed = False
                self.closure_reason = None
        else:
            self.consecutive_failures += 1
            self.total_failures += 1
            if branch_failed_hard(obs):
                self.is_closed = True
                self.closure_reason = "hard_unrecoverable"

    @property
    def latest_score(self) -> float:
        return self.scores[-1] if self.scores else 0.0

    @property
    def score_trend(self) -> float:
        if len(self.scores) < 2:
            return 0.0
        return self.scores[-1] - self.scores[-2]
