from __future__ import annotations

import math
from dream_rsi.core.models import ReplayEvaluationResult

class ReplayEvaluator:
    def __init__(self, beta_1: float = 0.01, beta_2: float = 0.05, lambda_penalty: float = 0.5):
        self.beta_1 = float(beta_1)
        self.beta_2 = float(beta_2)
        self.lambda_penalty = float(lambda_penalty)

    def calculate_replay_score(
        self,
        max_score: float,
        total_probes: int,
        decision_rounds: int,
    ) -> float:
        if total_probes <= 0:
            return max_score

        rounds = max(1, decision_rounds)
        parallelism_ratio = total_probes / rounds
        v_score = max_score - (self.beta_1 * total_probes) + (self.beta_2 * parallelism_ratio)
        return float(v_score)

    def calculate_batch_effective_sequential_rounds(self, batch_size: int, max_parallelism: int) -> int:
        if batch_size <= 0:
            return 0
        w = max(1, max_parallelism)
        return math.ceil(batch_size / w)

    def calculate_parallel_penalty(
        self,
        effective_sequential_rounds: float,
        total_probes: int,
    ) -> float:
        if total_probes <= 0:
            return 1.0
        return min(1.0, max(0.0, effective_sequential_rounds / total_probes))

    def calculate_pareto_auc(
        self,
        trajectory_curve: list[tuple[int, float]],
        max_budget: int = 100,
    ) -> float:
        if not trajectory_curve:
            return 0.0

        budget = max(1, max_budget)
        is_sorted = True
        for i in range(1, len(trajectory_curve)):
            if trajectory_curve[i][0] < trajectory_curve[i - 1][0]:
                is_sorted = False
                break

        points = trajectory_curve if is_sorted else sorted(trajectory_curve, key=lambda x: x[0])

        total_area = 0.0
        p_prev = 0
        s_prev = 0.0

        for p_curr, s_curr in points:
            p_effective = min(p_curr, budget)
            if p_effective > p_prev:
                total_area += s_prev * (p_effective - p_prev)
                p_prev = p_effective
            s_prev = s_curr
            if p_prev >= budget:
                break

        if p_prev < budget:
            total_area += s_prev * (budget - p_prev)

        return float(total_area / budget)

    def calculate_pareto_reward(self, pareto_auc: float, parallel_penalty: float) -> float:
        return float(pareto_auc - (self.lambda_penalty * parallel_penalty))

    def evaluate_episode(
        self,
        policy_name: str,
        beta: float,
        max_score: float,
        total_probes: int,
        decision_rounds: int,
        effective_sequential_rounds: float,
        trajectory_curve: list[tuple[int, float]],
        revealed_node_ids: list[str] | None = None,
        max_budget: int = 100,
    ) -> ReplayEvaluationResult:
        v_score = self.calculate_replay_score(max_score, total_probes, decision_rounds)
        parallel_pen = self.calculate_parallel_penalty(effective_sequential_rounds, total_probes)
        auc = self.calculate_pareto_auc(trajectory_curve, max_budget=max_budget)
        reward = self.calculate_pareto_reward(auc, parallel_pen)

        return ReplayEvaluationResult(
            policy_name=policy_name,
            beta=beta,
            max_score=max_score,
            total_probes=total_probes,
            decision_rounds=decision_rounds,
            effective_sequential_rounds=effective_sequential_rounds,
            replay_score=v_score,
            pareto_auc=auc,
            parallel_penalty=parallel_pen,
            pareto_reward=reward,
            revealed_node_ids=revealed_node_ids or [],
            trajectory_summary={
                "auc": auc,
                "parallel_penalty": parallel_pen,
                "replay_score": v_score,
            },
        )
