from __future__ import annotations

import math

from dream_rsi.core.models import GridPlan, GridPlanningContext
from dream_rsi.replay.question import QuestionAPI


class DynamicPortfolioPolicy:
    def __init__(
        self,
        name: str = "dynamic_portfolio",
        beta: float = 0.5,
        worker_cap: int = 10,
        enable_recovery: bool = True,
    ) -> None:
        self.name = name
        self.beta = min(1.0, max(0.0, float(beta)))
        self.worker_cap = max(1, int(worker_cap))
        self.enable_recovery = bool(enable_recovery)

    def step(self, question: QuestionAPI) -> list[str]:
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

        leaves = [nid for nid in admissible if nid != root_id and nid in unrevealed_cand]

        recovery_candidates = [
            nid for nid in leaves
            if observed[nid].observation.is_repairable
        ]

        exploitation_candidates = [
            nid for nid in leaves
            if nid not in recovery_candidates
        ]
        exploitation_candidates.sort(
            key=lambda x: observed[x].observation.score,
            reverse=True,
        )

        batch: list[str] = []

        if self.enable_recovery and recovery_candidates and len(batch) < self.worker_cap:
            batch.append(recovery_candidates[0])

        remaining_slots = self.worker_cap - len(batch)
        if remaining_slots <= 0:
            return batch

        target_exploit = int(math.floor(remaining_slots * self.beta))
        exploit_allocated = 0

        for cand in exploitation_candidates:
            if exploit_allocated >= target_exploit or len(batch) >= self.worker_cap:
                break
            batch.append(cand)
            exploit_allocated += 1

        while len(batch) < self.worker_cap and root_id in unrevealed_cand:
            batch.append(root_id)

        if len(batch) < self.worker_cap:
            for cand in exploitation_candidates:
                if cand not in batch:
                    batch.append(cand)
                    if len(batch) >= self.worker_cap:
                        break

        return batch

    @staticmethod
    def plan_grid(context: GridPlanningContext) -> GridPlan:
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
                reason="Cold start: initialized width to worker cap and conservative depth.",
            )

        avg_depth = sum(t.max_depth for t in context.history) / total_trees
        success_count = sum(1 for t in context.history if t.best_score > 0.0)
        success_ratio = success_count / total_trees

        if success_ratio >= 0.7:
            w = min(hard_max_w, max(2, int(w_cap * 1.5)))
            r = min(hard_max_r, max(2, int(avg_depth + 2)))
            reason = "High success history: scaled width and depth for aggressive exploitation."
        else:
            w = min(hard_max_w, max(4, w_cap * 2))
            r = min(hard_max_r, max(1, int(avg_depth * 0.8) or 2))
            reason = "Exploration phase: widened branch count and bounded refinement depth."

        return GridPlan(branch_count=w, refine_count=r, reason=reason)
