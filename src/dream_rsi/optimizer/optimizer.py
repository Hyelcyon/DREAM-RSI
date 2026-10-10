from __future__ import annotations

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


class PolicyOptimizer:
    def __init__(
        self,
        simulator: ReplaySimulator | None = None,
        evaluator: ReplayEvaluator | None = None,
    ) -> None:
        self.evaluator = evaluator or ReplayEvaluator()
        self.simulator = simulator or ReplaySimulator(evaluator=self.evaluator)

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
