from __future__ import annotations

import math
from pydantic import BaseModel, Field


class LassoInstance(BaseModel):
    n_samples: int
    n_features: int
    lambdas: list[float]


class LassoEvaluationResult(BaseModel):
    is_correct: bool
    max_objective_violation: float
    runtime_ms: float
    search_score: float
    error: str | None = None


class LassoEvaluator:
    """Evaluates Lasso regularization path solvers from paper Appendix A Problem 1:

    F_k(w) = (1 / 2n) ||y - Xw||_2^2 + lambda_k ||w||_1
    Correctness tolerance: F_k(w) <= F_k(w_ref) + 1e-6
    Search score: R_search = (prod t_i)^(-1 / |I|)
    """

    @staticmethod
    def soft_threshold(z: float, gamma: float) -> float:
        if abs(z) <= gamma:
            return 0.0
        return math.copysign(abs(z) - gamma, z)

    @classmethod
    def compute_objective(
        cls,
        x_rows: list[list[float]],
        y: list[float],
        w: list[float],
        lam: float,
    ) -> float:
        n = len(y)
        p = len(w)
        loss = 0.0
        for i in range(n):
            pred = sum(x_rows[i][j] * w[j] for j in range(p))
            err = y[i] - pred
            loss += err * err
        l1 = sum(abs(v) for v in w)
        return (loss / (2.0 * n)) + (lam * l1)

    @classmethod
    def solve_coordinate_descent(
        cls,
        x_rows: list[list[float]],
        y: list[float],
        lam_path: list[float],
        max_iter: int = 1000,
        tol: float = 1e-6,
    ) -> list[list[float]]:
        n = len(y)
        p = len(x_rows[0])
        col_norms = [sum(x_rows[i][j] ** 2 for i in range(n)) / n for j in range(p)]

        coef_path: list[list[float]] = []
        w = [0.0] * p

        for lam in lam_path:
            for _ in range(max_iter):
                dmax = 0.0
                for j in range(p):
                    if col_norms[j] <= 1e-12:
                        continue
                    old_wj = w[j]
                    res_j = 0.0
                    for i in range(n):
                        pred_except_j = sum(x_rows[i][k] * w[k] for k in range(p) if k != j)
                        res_j += x_rows[i][j] * (y[i] - pred_except_j)
                    res_j /= n
                    new_wj = cls.soft_threshold(res_j, lam) / col_norms[j]
                    diff = abs(new_wj - old_wj)
                    if diff > dmax:
                        dmax = diff
                    w[j] = new_wj
                if dmax < tol:
                    break
            coef_path.append(list(w))

        return coef_path

    @classmethod
    def evaluate_solution(
        cls,
        x_rows: list[list[float]],
        y: list[float],
        lam_path: list[float],
        candidate_path: list[list[float]],
        runtime_ms: float,
        tol: float = 1e-6,
    ) -> LassoEvaluationResult:
        if len(candidate_path) != len(lam_path):
            return LassoEvaluationResult(
                is_correct=False,
                max_objective_violation=float("inf"),
                runtime_ms=runtime_ms,
                search_score=0.0,
                error="Path length mismatch.",
            )

        ref_path = cls.solve_coordinate_descent(x_rows, y, lam_path)
        max_viol = 0.0

        for k, lam in enumerate(lam_path):
            cand_obj = cls.compute_objective(x_rows, y, candidate_path[k], lam)
            ref_obj = cls.compute_objective(x_rows, y, ref_path[k], lam)
            viol = cand_obj - ref_obj
            if viol > max_viol:
                max_viol = viol

        is_correct = max_viol <= tol
        score = (1000.0 / max(1.0, runtime_ms)) if is_correct else 0.0

        return LassoEvaluationResult(
            is_correct=is_correct,
            max_objective_violation=float(max_viol),
            runtime_ms=float(runtime_ms),
            search_score=float(score),
            error=None if is_correct else f"Objective tolerance exceeded by {max_viol:.2e}",
        )

    @staticmethod
    def calculate_geometric_mean_search_score(instance_runtimes_sec: list[float]) -> float:
        """Computes paper Equation: R_search = (prod_{i in I} t_i)^(-1 / |I|)."""
        if not instance_runtimes_sec:
            return 0.0
        n = len(instance_runtimes_sec)
        # Prevent division by zero and negative timings
        safe_times = [max(1e-9, float(t)) for t in instance_runtimes_sec]
        # Compute in log space to avoid numerical underflow/overflow: exp(-1/n * sum(log(t_i)))
        log_sum = sum(math.log(t) for t in safe_times)
        return float(math.exp(-log_sum / n))
