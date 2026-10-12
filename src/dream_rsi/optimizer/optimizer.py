from __future__ import annotations

from collections import deque

from pydantic import BaseModel

from dream_rsi.core.evaluator import ReplayEvaluator
from dream_rsi.core.models import DiscoveryTree
from dream_rsi.optimizer.policy import DynamicPortfolioPolicy
from dream_rsi.replay.simulator import ReplaySimulator


class FrontierPoint(BaseModel):
    beta: float
    mean_replay_score: float
    mean_pareto_reward: float
    mean_pareto_auc: float
    mean_parallel_penalty: float
    is_non_dominated: bool = True


class PolicyEvaluationSummary(BaseModel):
    name: str
    beta: float
    replay_score: float
    pareto_reward: float
    pareto_auc: float
    parallel_penalty: float


class PolicyComparisonResult(BaseModel):
    baseline: PolicyEvaluationSummary
    candidate: PolicyEvaluationSummary
    delta_replay_score: float
    delta_pareto_reward: float
    is_improved: bool
    trees_evaluated: int


class OptimalSelectionResult(BaseModel):
    selected_policy: str
    selected_beta: float
    selected_replay_score: float
    selected_pareto_reward: float
    baseline_replay_score: float
    monotonicity_verified: bool
    improvement: float


class CrossCycleBetaResult(BaseModel):
    recommended_beta: float
    prior_beta: float
    reason: str
    is_adjusted: bool


class PolicyOptimizer:
    def __init__(
        self,
        simulator: ReplaySimulator | None = None,
        evaluator: ReplayEvaluator | None = None,
    ) -> None:
        self.evaluator = evaluator or ReplayEvaluator()
        self.simulator = simulator or ReplaySimulator(evaluator=self.evaluator)

    @staticmethod
    def is_dominated(p1: FrontierPoint, p2: FrontierPoint) -> bool:
        """Determines if p2 dominates p1 across multi-objective Pareto dimensions."""
        score_diff = p2.mean_replay_score - p1.mean_replay_score
        reward_diff = p2.mean_pareto_reward - p1.mean_pareto_reward
        at_least_as_good = score_diff >= -1e-9 and reward_diff >= -1e-9
        strictly_better = score_diff > 1e-6 or reward_diff > 1e-6
        return at_least_as_good and strictly_better

    @classmethod
    def filter_non_dominated(cls, points: list[FrontierPoint]) -> list[FrontierPoint]:
        """Extracts strictly non-dominated points on the empirical Pareto frontier."""
        if len(points) <= 1:
            return list(points)

        pts = sorted(
            points,
            key=lambda x: (x.mean_replay_score, x.mean_pareto_reward),
            reverse=True,
        )
        n = len(pts)

        max_y_strict = float("-inf")
        left = 0
        right = 0
        deq: deque[tuple[int, float]] = deque()
        non_dominated: list[FrontierPoint] = []

        for i in range(n):
            curr = pts[i]
            curr_x = curr.mean_replay_score
            curr_y = curr.mean_pareto_reward

            while left < n and pts[left].mean_replay_score > curr_x + 1e-6:
                if pts[left].mean_pareto_reward > max_y_strict:
                    max_y_strict = pts[left].mean_pareto_reward
                left += 1

            if max_y_strict >= curr_y - 1e-9:
                continue

            while right < n and pts[right].mean_replay_score >= curr_x - 1e-9:
                val = pts[right].mean_pareto_reward
                while deq and deq[-1][1] <= val:
                    deq.pop()
                deq.append((right, val))
                right += 1

            while deq and deq[0][0] < left:
                deq.popleft()

            if deq and deq[0][1] > curr_y + 1e-6:
                continue

            non_dominated.append(curr)

        return non_dominated

    def evaluate_frontier(
        self,
        trees: list[DiscoveryTree],
        beta_steps: int = 5,
        worker_cap: int = 10,
        max_budget: int = 100,
    ) -> list[FrontierPoint]:
        steps = max(2, int(beta_steps))
        betas = [round(i / (steps - 1), 3) for i in range(steps)]
        frontier: list[FrontierPoint] = []

        for b in betas:
            pol = DynamicPortfolioPolicy(
                name=f"portfolio_beta_{b}",
                beta=b,
                worker_cap=worker_cap,
            )
            eval_result = self.simulator.run_multi_tree(pol, trees, max_budget=max_budget)
            frontier.append(FrontierPoint(
                beta=b,
                mean_replay_score=eval_result.mean_replay_score,
                mean_pareto_reward=eval_result.mean_pareto_reward,
                mean_pareto_auc=eval_result.mean_pareto_auc,
                mean_parallel_penalty=eval_result.mean_parallel_penalty,
            ))

        for p in frontier:
            dominated = any(self.is_dominated(p, other) for other in frontier if other is not p)
            p.is_non_dominated = not dominated

        frontier.sort(key=lambda x: x.mean_replay_score, reverse=True)
        return frontier

    def compare_policies(
        self,
        candidate_policy: DynamicPortfolioPolicy,
        baseline_policy: DynamicPortfolioPolicy,
        trees: list[DiscoveryTree],
        max_budget: int = 100,
    ) -> PolicyComparisonResult:
        cand_res = self.simulator.run_multi_tree(candidate_policy, trees, max_budget=max_budget)
        base_res = self.simulator.run_multi_tree(baseline_policy, trees, max_budget=max_budget)

        cand_score = cand_res.mean_replay_score
        base_score = base_res.mean_replay_score
        delta = cand_score - base_score

        cand_reward = cand_res.mean_pareto_reward
        base_reward = base_res.mean_pareto_reward
        delta_reward = cand_reward - base_reward

        is_improved = delta > 0 or (delta == 0 and delta_reward > 0)

        return PolicyComparisonResult(
            baseline=PolicyEvaluationSummary(
                name=baseline_policy.name,
                beta=baseline_policy.beta,
                replay_score=base_score,
                pareto_reward=base_reward,
                pareto_auc=base_res.mean_pareto_auc,
                parallel_penalty=base_res.mean_parallel_penalty,
            ),
            candidate=PolicyEvaluationSummary(
                name=candidate_policy.name,
                beta=candidate_policy.beta,
                replay_score=cand_score,
                pareto_reward=cand_reward,
                pareto_auc=cand_res.mean_pareto_auc,
                parallel_penalty=cand_res.mean_parallel_penalty,
            ),
            delta_replay_score=delta,
            delta_pareto_reward=delta_reward,
            is_improved=is_improved,
            trees_evaluated=len(trees),
        )

    def select_optimal_policy(
        self,
        candidate_policies: list[DynamicPortfolioPolicy],
        baseline_policy: DynamicPortfolioPolicy,
        trees: list[DiscoveryTree],
        max_budget: int = 100,
    ) -> tuple[DynamicPortfolioPolicy, OptimalSelectionResult]:
        all_candidates = [baseline_policy] + [
            p for p in candidate_policies if p.name != baseline_policy.name
        ]

        best_policy = baseline_policy
        best_eval = self.simulator.run_multi_tree(baseline_policy, trees, max_budget=max_budget)
        base_eval = best_eval

        for cand in all_candidates[1:]:
            cand_eval = self.simulator.run_multi_tree(cand, trees, max_budget=max_budget)
            if cand_eval.mean_replay_score > best_eval.mean_replay_score:
                best_policy = cand
                best_eval = cand_eval
            elif (
                cand_eval.mean_replay_score == best_eval.mean_replay_score
                and cand_eval.mean_pareto_reward > best_eval.mean_pareto_reward
            ):
                best_policy = cand
                best_eval = cand_eval

        assert best_eval.mean_replay_score >= base_eval.mean_replay_score, (
            f"Monotonicity violation: selected score {best_eval.mean_replay_score} "
            f"< baseline score {base_eval.mean_replay_score}"
        )

        comparison = OptimalSelectionResult(
            selected_policy=best_policy.name,
            selected_beta=best_policy.beta,
            selected_replay_score=best_eval.mean_replay_score,
            selected_pareto_reward=best_eval.mean_pareto_reward,
            baseline_replay_score=base_eval.mean_replay_score,
            monotonicity_verified=True,
            improvement=best_eval.mean_replay_score - base_eval.mean_replay_score,
        )
        return best_policy, comparison

    def select_cross_cycle_beta(
        self,
        history_scores: list[float],
        current_beta: float,
        sweep_frontier: list[FrontierPoint],
    ) -> CrossCycleBetaResult:
        """Applies cross-cycle default beta adaptation rule from paper Listing 2."""
        curr_b = min(1.0, max(0.0, float(current_beta)))
        if len(history_scores) < 2 or not sweep_frontier:
            default_b = 0.6 if not history_scores else curr_b
            return CrossCycleBetaResult(
                recommended_beta=default_b,
                prior_beta=curr_b,
                reason="History is insufficient or empty: adopting exploratory default beta=0.6.",
                is_adjusted=(default_b != curr_b),
            )

        best_sweep = max(sweep_frontier, key=lambda p: (p.mean_pareto_reward, p.mean_replay_score))
        score_diff = history_scores[-1] - history_scores[-2]

        if score_diff > 1e-4:
            return CrossCycleBetaResult(
                recommended_beta=curr_b,
                prior_beta=curr_b,
                reason="Live best score is still actively improving: retaining current default beta.",
                is_adjusted=False,
            )

        if best_sweep.beta > curr_b and best_sweep.mean_pareto_reward > 0.0:
            new_b = min(1.0, round(curr_b + 0.15, 2))
            return CrossCycleBetaResult(
                recommended_beta=new_b,
                prior_beta=curr_b,
                reason="Live best plateaued and sweep demonstrates higher attainment: raising beta by +0.15.",
                is_adjusted=True,
            )

        if best_sweep.beta < curr_b:
            new_b = max(0.0, round(curr_b - 0.15, 2))
            return CrossCycleBetaResult(
                recommended_beta=new_b,
                prior_beta=curr_b,
                reason="High beta adds work without higher attainment: lowering beta by -0.15.",
                is_adjusted=True,
            )

        return CrossCycleBetaResult(
            recommended_beta=curr_b,
            prior_beta=curr_b,
            reason="Live best plateaued and sweep confirms current beta is balanced.",
            is_adjusted=False,
        )

