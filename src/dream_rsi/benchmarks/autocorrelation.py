from __future__ import annotations

import math
from pydantic import BaseModel, Field


class AutocorrelationResult(BaseModel):
    is_valid: bool
    is_non_negative: bool = True
    phi_1: float = 0.0
    phi_2: float = 0.0
    phi_3: float = 0.0
    integral_mass: float = 1.0
    error: str | None = None


class AutocorrelationEvaluator:
    """Evaluates autocorrelation inequalities from paper Appendix A Problem 4:

    f supported on [-1/4, 1/4] with int_{-1/4}^{1/4} f(x) dx = 1
    (f * f)(t) = int f(t - x) f(x) dx, t in [-1/2, 1/2]
    Phi_1(f) = max_t (f * f)(t)  (minimize, f >= 0)
    Phi_2(f) = ||f * f||_2^2 / (||f * f||_1 * ||f * f||_inf)  (maximize, f >= 0)
    Phi_3(f) = max_t |(f * f)(t)|  (minimize, possibly signed)
    """

    @staticmethod
    def evaluate(grid_values: list[float], dx: float | None = None) -> AutocorrelationResult:
        n = len(grid_values)
        if n < 3:
            return AutocorrelationResult(
                is_valid=False,
                is_non_negative=False,
                error="Grid must contain at least 3 sample points.",
            )

        if dx is None:
            dx = 0.5 / (n - 1)

        is_non_neg = all(v >= -1e-9 for v in grid_values)
        mass = (sum(grid_values) - 0.5 * (grid_values[0] + grid_values[-1])) * dx
        if mass <= 0.0 or not math.isfinite(mass):
            return AutocorrelationResult(
                is_valid=False,
                is_non_negative=is_non_neg,
                error=f"Invalid non-positive integral mass {mass}.",
            )

        f_norm = [v / mass for v in grid_values]

        conv_len = 2 * n - 1
        conv: list[float] = [0.0] * conv_len

        for i in range(n):
            fi = f_norm[i]
            for j in range(n):
                conv[i + j] += fi * f_norm[j] * dx

        phi_1 = max(conv)
        phi_3 = max(abs(v) for v in conv)

        l1_norm = sum(abs(v) for v in conv) * dx
        l2_sq = sum(v * v for v in conv) * dx
        linf_norm = phi_3

        denom = l1_norm * linf_norm
        phi_2 = (l2_sq / denom) if denom > 1e-12 else 0.0

        return AutocorrelationResult(
            is_valid=True,
            is_non_negative=is_non_neg,
            phi_1=float(phi_1),
            phi_2=float(phi_2),
            phi_3=float(phi_3),
            integral_mass=float(mass),
            error=None,
        )

    @staticmethod
    def uniform_density_baseline(num_points: int = 101) -> list[float]:
        """Returns uniform density function f(x) = 2 on [-1/4, 1/4]."""
        return [2.0] * num_points
