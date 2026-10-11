from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field

from dream_rsi.core.evaluator import ReplayEvaluator
from dream_rsi.core.models import DiscoveryTree, ReplayEvaluationResult, TreeNode
from dream_rsi.replay.question import QuestionAPI


class SearchPolicy(Protocol):
    name: str
    beta: float
    worker_cap: int

    def step(self, question: QuestionAPI) -> list[str]:
        ...

    def solve(self, question: QuestionAPI, budget: int | None = None) -> list[TreeNode]:
        ...


def _default_episodes() -> list[ReplayEvaluationResult]:
    return []


class MultiTreeEvaluationResult(BaseModel):
    policy_name: str
    beta: float
    mean_replay_score: float
    mean_pareto_reward: float
    mean_pareto_auc: float
    mean_parallel_penalty: float
    total_trees: int
    episodes: list[ReplayEvaluationResult] = Field(default_factory=_default_episodes)


class ReplaySimulator:
    def __init__(self, evaluator: ReplayEvaluator | None = None) -> None:
        self.evaluator = evaluator or ReplayEvaluator()

    def run_episode(
        self,
        policy: SearchPolicy,
        tree: DiscoveryTree,
        max_budget: int = 100,
    ) -> ReplayEvaluationResult:
        question = QuestionAPI(
            tree=tree,
            max_parallelism=policy.worker_cap,
            max_budget=max_budget,
        )

        policy.solve(question, budget=max_budget)

        revealed_scores = [
            node.observation.score
            for node in question.observed().values()
            if node.observation.evaluated
        ]
        max_score = max(revealed_scores) if revealed_scores else 0.0

        return self.evaluator.evaluate_episode(
            policy_name=policy.name,
            beta=policy.beta,
            max_score=max_score,
            total_probes=question.probes_spent,
            decision_rounds=question.rounds_spent,
            effective_sequential_rounds=question.effective_sequential_rounds,
            trajectory_curve=question.trajectory,
            revealed_node_ids=question.revealed_node_ids,
            max_budget=max_budget,
        )

    def run_multi_tree(
        self,
        policy: SearchPolicy,
        trees: list[DiscoveryTree],
        max_budget: int = 100,
    ) -> MultiTreeEvaluationResult:
        if not trees:
            return MultiTreeEvaluationResult(
                policy_name=policy.name,
                beta=policy.beta,
                mean_replay_score=0.0,
                mean_pareto_reward=0.0,
                mean_pareto_auc=0.0,
                mean_parallel_penalty=0.0,
                total_trees=0,
                episodes=[],
            )

        episodes: list[ReplayEvaluationResult] = []
        for tree in trees:
            res = self.run_episode(policy, tree, max_budget=max_budget)
            episodes.append(res)

        mean_replay_score = sum(e.replay_score for e in episodes) / len(episodes)
        mean_pareto_reward = sum(e.pareto_reward for e in episodes) / len(episodes)
        mean_pareto_auc = sum(e.pareto_auc for e in episodes) / len(episodes)
        mean_parallel_penalty = sum(e.parallel_penalty for e in episodes) / len(episodes)

        return MultiTreeEvaluationResult(
            policy_name=policy.name,
            beta=policy.beta,
            mean_replay_score=float(mean_replay_score),
            mean_pareto_reward=float(mean_pareto_reward),
            mean_pareto_auc=float(mean_pareto_auc),
            mean_parallel_penalty=float(mean_parallel_penalty),
            total_trees=len(trees),
            episodes=episodes,
        )
