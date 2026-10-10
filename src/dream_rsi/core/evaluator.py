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

        sorted_points = sorted(trajectory_curve, key=lambda x: x[0])
        if sorted_points[0][0] > 0:
            sorted_points.insert(0, (0, 0.0))

        last_probes, last_score = sorted_points[-1]
        if last_probes < max_budget:
            sorted_points.append((max_budget, last_score))

        total_area = 0.0
        for i in range(1, len(sorted_points)):
            p_prev, s_prev = sorted_points[i - 1]
            p_curr, _ = sorted_points[i]
            delta_p = p_curr - p_prev
            total_area += s_prev * delta_p

        normalized_auc = total_area / max(1, max_budget)
        return float(normalized_auc)

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
