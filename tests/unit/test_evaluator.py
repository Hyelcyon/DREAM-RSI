import pytest
from dream_rsi.core.evaluator import ReplayEvaluator


def test_calculate_replay_score_equation_1():
    evaluator = ReplayEvaluator(beta_1=0.01, beta_2=0.05)

    max_score = 1.0
    total_probes = 20
    decision_rounds = 4

    score = evaluator.calculate_replay_score(
        max_score=max_score,
        total_probes=total_probes,
        decision_rounds=decision_rounds,
    )
    assert pytest.approx(score, rel=1e-5) == 1.05


def test_batch_effective_sequential_rounds():
    evaluator = ReplayEvaluator()

    assert evaluator.calculate_batch_effective_sequential_rounds(batch_size=10, max_parallelism=10) == 1
    assert evaluator.calculate_batch_effective_sequential_rounds(batch_size=11, max_parallelism=10) == 2
    assert evaluator.calculate_batch_effective_sequential_rounds(batch_size=1, max_parallelism=10) == 1
    assert evaluator.calculate_batch_effective_sequential_rounds(batch_size=0, max_parallelism=10) == 0


def test_parallel_penalty():
    evaluator = ReplayEvaluator()

    serial_penalty = evaluator.calculate_parallel_penalty(effective_sequential_rounds=10.0, total_probes=10)
    assert pytest.approx(serial_penalty, rel=1e-5) == 1.0

    parallel_penalty = evaluator.calculate_parallel_penalty(effective_sequential_rounds=1.0, total_probes=10)
    assert pytest.approx(parallel_penalty, rel=1e-5) == 0.1


def test_pareto_auc_and_reward():
    evaluator = ReplayEvaluator(lambda_penalty=0.5)

    curve = [(10, 0.5), (20, 1.0)]
    auc = evaluator.calculate_pareto_auc(curve, max_budget=20)
    assert pytest.approx(auc, rel=1e-5) == 0.25

    penalty = 0.2
    reward = evaluator.calculate_pareto_reward(auc, penalty)
    assert pytest.approx(reward, rel=1e-5) == 0.15
