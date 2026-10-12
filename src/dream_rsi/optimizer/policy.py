from __future__ import annotations

import math
from typing import Any

from dream_rsi.core.models import GridPlan, GridPlanningContext, TreeNode
from dream_rsi.core.signals import (
    BranchTrajectory,
    branch_failed_hard,
    branch_promising,
)
from dream_rsi.replay.question import QuestionAPI


class OptimalPolicy:
    NAME = "OptimalPolicy"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config: dict[str, Any] = config or {}
        self.name: str = str(self.config.get("name", self.NAME))
        self.beta: float = min(1.0, max(0.0, float(self.config.get("beta", 0.6))))
        self.worker_cap: int = max(1, int(self.config.get("worker_cap", 10)))
        self.schedule: dict[str, float] = self._schedule(self.beta)

    def _schedule(self, beta: float) -> dict[str, float]:
        """Routes behavioral parameters through single beta scalar."""
        return {
            "patience": float(max(1, int(2 + round(4 * beta)))),
            "min_gain": float(max(0.0, 0.05 * (1.0 - beta))),
            "exploit_ratio": float(max(0.2, min(0.8, beta))),
            "stagnation_limit": float(max(2, int(3 + round(5 * beta)))),
            "reserve_threshold": float(0.1 * (1.0 - beta)),
        }

    def reconstruct_trajectories(
        self,
        question: QuestionAPI,
        observed: dict[str, TreeNode] | None = None,
    ) -> dict[int, BranchTrajectory]:
        """Reconstructs ordered prefix trajectories for each branch observed so far."""
        if observed is None:
            observed = question.observed()
        branches: dict[int, list[TreeNode]] = {}
        for node in observed.values():
            if node.is_root:
                continue
            b_id = node.branch_id
            if b_id not in branches:
                branches[b_id] = []
            branches[b_id].append(node)

        for b_nodes in branches.values():
            b_nodes.sort(key=lambda n: n.depth)

        trajectories: dict[int, BranchTrajectory] = {}
        for b_id, b_nodes in branches.items():
            trajectories[b_id] = BranchTrajectory.from_nodes(b_id, b_nodes)

        return trajectories

    def step(self, question: QuestionAPI) -> list[str]:
        """Builds one dynamic portfolio batch up to max_parallelism."""
        w_cap = min(self.worker_cap, question.max_parallelism)
        admissible = question.admissible_continuations()
        unrevealed_cand = question.get_unrevealed_continuations()
        if not unrevealed_cand:
            return []

        observed = question.observed()
        root_id = list(observed.keys())[0] if observed else "root"
        for nid, node in observed.items():
            if node.is_root:
                root_id = nid
                break

        trajectories = self.reconstruct_trajectories(question, observed=observed)
        patience = int(self.schedule["patience"])

        closed_branches: set[int] = set()
        for b_id, traj in trajectories.items():
            if traj.is_closed:
                closed_branches.add(b_id)
            elif traj.consecutive_failures >= patience and not traj.has_successful_anchor:
                closed_branches.add(b_id)

        legal_roots = question.legal_roots()
        unopened_roots = [r for r in legal_roots if r in unrevealed_cand]

        eligible_frontiers: list[str] = []
        recovery_candidates: list[str] = []

        for nid in admissible:
            if nid == root_id or nid not in unrevealed_cand:
                continue
            node = observed[nid]
            b_id = node.branch_id
            if b_id in closed_branches:
                continue

            obs = node.observation
            if obs.is_repairable and not branch_failed_hard(obs):
                recovery_candidates.append(nid)
            else:
                eligible_frontiers.append(nid)

        def score_frontier(nid: str) -> float:
            if nid == root_id or nid in unopened_roots:
                return float(question.baseline_score)
            node = observed.get(nid)
            if node is None:
                return 0.0
            b_id = node.branch_id
            traj = trajectories.get(b_id)
            base_s = node.observation.score if node.observation.evaluated else 0.0
            anchor_s = traj.successful_anchor_score if traj else base_s
            trend = traj.score_trend if traj else 0.0
            return float(anchor_s + (0.5 * trend) + (0.1 * node.observation.delta_vs_parent))

        strong_refinements: list[str] = []
        underexplored_frontiers: list[str] = []

        for nid in eligible_frontiers:
            node = observed[nid]
            traj = trajectories.get(node.branch_id)
            if traj and (traj.has_successful_anchor or traj.score_trend > 0):
                strong_refinements.append(nid)
            else:
                underexplored_frontiers.append(nid)

        strong_refinements.sort(key=score_frontier, reverse=True)
        underexplored_frontiers.sort(key=score_frontier, reverse=True)
        recovery_candidates.sort(key=score_frontier, reverse=True)

        exploration_pool = unopened_roots + underexplored_frontiers

        batch: list[str] = []

        def can_add(candidate_id: str) -> bool:
            if candidate_id in batch:
                return False
            for existing_id in batch:
                if question._is_ancestor_in_observed(existing_id, candidate_id):
                    return False
                if question._is_ancestor_in_observed(candidate_id, existing_id):
                    return False
            return True

        # Role 1: Justified recovery (at most one recovery slot)
        if recovery_candidates and len(batch) < w_cap:
            for cand in recovery_candidates:
                if can_add(cand):
                    batch.append(cand)
                    break

        # Role 2: Exploration representation (give representation before filling remaining slots)
        if exploration_pool and len(batch) < w_cap:
            for cand in exploration_pool:
                if can_add(cand):
                    batch.append(cand)
                    break

        # Role 3: Exploitation representation (strong refinements)
        if strong_refinements and len(batch) < w_cap:
            exploit_target = max(1, int(math.floor((w_cap - len(batch)) * self.schedule["exploit_ratio"])))
            count = 0
            for cand in strong_refinements:
                if count >= exploit_target or len(batch) >= w_cap:
                    break
                if can_add(cand):
                    batch.append(cand)
                    count += 1

        # Fill remaining slots up to w_cap by highest overall priority
        all_remaining = strong_refinements + exploration_pool + recovery_candidates
        all_remaining.sort(key=score_frontier, reverse=True)
        for cand in all_remaining:
            if len(batch) >= w_cap:
                break
            if can_add(cand):
                batch.append(cand)

        return batch

    def solve(self, question: QuestionAPI, budget: int | None = None) -> list[TreeNode]:
        """Executes full exploration rollout over question environment."""
        question.reset()
        revealed: list[TreeNode] = []
        while not question.is_exhausted():
            if budget is not None and question.probes_spent >= budget:
                break
            batch = self.step(question)
            if not batch:
                break
            newly_revealed = question.probe_batch(batch)
            if not newly_revealed:
                break
            revealed.extend(newly_revealed)
        return revealed

    @classmethod
    def plan_grid(cls, context: GridPlanningContext) -> GridPlan:
        """Determines width W and depth R based on historical discovery evidence."""
        w_cap = context.worker_cap
        hard_max_w = context.hard_max_branch_count
        hard_max_r = context.hard_max_refine_count

        total_trees = len(context.history)
        if total_trees == 0:
            w = min(hard_max_w, max(2, w_cap))
            r = min(hard_max_r, 4)
            return GridPlan(
                branch_count=w,
                refine_count=r,
                reason="Conflicting or insufficient history: returned explicit conservative bootstrap plan.",
            )

        avg_depth = sum(t.max_depth for t in context.history) / total_trees
        total_early_imp = sum(t.early_improvements for t in context.history)
        total_stalled_deep = sum(t.stalled_deep_refinements for t in context.history)
        total_late_gains = sum(t.late_high_gains for t in context.history)
        total_hard_fails = sum(t.hard_failures for t in context.history)
        total_plateaued = sum(t.plateaued_branches for t in context.history)

        # Rule 1: Many distinct roots improve early while deeper refinements stall
        if total_early_imp > 0 and total_stalled_deep >= total_early_imp:
            w = min(hard_max_w, max(2, int(round(w_cap * 1.3))))
            r = max(2, min(hard_max_r, int(round(avg_depth * 0.75))))
            return GridPlan(
                branch_count=w,
                refine_count=r,
                reason="Many distinct roots improved early while deeper refinements stalled: increased width W and held depth R.",
            )

        # Rule 2: High gains arrive late on a small, repeatable set of directions
        if total_late_gains > 0 and total_late_gains >= total_early_imp:
            w = min(hard_max_w, max(2, int(round(w_cap * 0.8))))
            r = min(hard_max_r, max(4, int(round(avg_depth * 1.5))))
            return GridPlan(
                branch_count=w,
                refine_count=r,
                reason="High gains arrived late on a repeatable set of directions: reduced width W and increased depth R.",
            )

        # Rule 3: Repeated hard, unrecoverable failures or strongly redundant directions
        if total_hard_fails >= 2:
            w = max(2, min(hard_max_w, int(round(w_cap * 0.7))))
            r = max(2, min(hard_max_r, int(round(avg_depth * 0.7))))
            return GridPlan(
                branch_count=w,
                refine_count=r,
                reason="Repeated hard unrecoverable failures detected: reduced width W and depth R conservatively.",
            )

        # Rule 4: All explored directions plateau after sufficient depth while meaningful directions remain
        if total_plateaued > 0 and total_plateaued >= total_early_imp:
            w = min(hard_max_w, max(4, int(round(w_cap * 1.2))))
            r = max(2, min(hard_max_r, int(round(avg_depth * 0.8))))
            return GridPlan(
                branch_count=w,
                refine_count=r,
                reason="Explored directions plateaued after depth: increased width W to uncover new directions.",
            )

        # Rule 5: Macro success ratio calibration when granular branch signals are absent
        success_count = sum(1 for t in context.history if t.best_score > 0.0)
        success_ratio = success_count / total_trees

        if success_ratio > 0.5:
            w = min(hard_max_w, max(2, int(w_cap * 0.8)))
            r = min(hard_max_r, int(avg_depth * 1.5))
            return GridPlan(
                branch_count=w,
                refine_count=r,
                reason="High success history: narrowed width and deepened refinement.",
            )

        if success_ratio < 0.25:
            w = min(hard_max_w, max(4, int(w_cap * 1.5)))
            r = max(2, int(avg_depth * 0.75))
            return GridPlan(
                branch_count=w,
                refine_count=r,
                reason="Low early success rate: expanded hypothesis width W to sample diverse roots.",
            )

        # Rule 6: Balanced default empirical calibration
        w = min(hard_max_w, max(2, w_cap))
        r = min(hard_max_r, max(3, int(round(avg_depth))))
        return GridPlan(
            branch_count=w,
            refine_count=r,
            reason="Balanced empirical progress: calibrated grid to historical average depth.",
        )


class DynamicPortfolioPolicy(OptimalPolicy):
    def __init__(
        self,
        name: str = "dynamic_portfolio",
        beta: float = 0.5,
        worker_cap: int = 10,
        enable_recovery: bool = True,
    ) -> None:
        super().__init__(config={
            "name": name,
            "beta": beta,
            "worker_cap": worker_cap,
            "enable_recovery": enable_recovery,
        })
