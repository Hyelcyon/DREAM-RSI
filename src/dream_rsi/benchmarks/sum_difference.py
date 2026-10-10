from __future__ import annotations

import math
from pydantic import BaseModel, Field


class SumDifferenceResult(BaseModel):
    is_valid: bool
    size: int
    sumset_size: int
    diffset_size: int
    gamma_score: float
    error: str | None = None


class SumDifferenceEvaluator:
    """Evaluates finite integer subsets A on the normalized sum-difference objective:

    Gamma(A) = log(|A + A| / |A|) / log(|A - A| / |A|)
    """

    @staticmethod
    def evaluate(elements: list[int] | set[int]) -> SumDifferenceResult:
        unique_a = sorted(list(set(elements)))
        size = len(unique_a)
        if size < 2:
            return SumDifferenceResult(
                is_valid=False,
                size=size,
                sumset_size=0,
                diffset_size=0,
                gamma_score=0.0,
                error="Set must contain at least 2 distinct integers.",
            )

        sumset = {a1 + a2 for a1 in unique_a for a2 in unique_a}
        diffset = {a1 - a2 for a1 in unique_a for a2 in unique_a}

        len_sum = len(sumset)
        len_diff = len(diffset)

        ratio_sum = len_sum / size
        ratio_diff = len_diff / size

        if ratio_diff <= 1.0 or ratio_sum <= 1.0:
            return SumDifferenceResult(
                is_valid=False,
                size=size,
                sumset_size=len_sum,
                diffset_size=len_diff,
                gamma_score=0.0,
                error="Trivial degenerate set ratios.",
            )

        gamma = math.log(ratio_sum) / math.log(ratio_diff)
        return SumDifferenceResult(
            is_valid=True,
            size=size,
            sumset_size=len_sum,
            diffset_size=len_diff,
            gamma_score=float(gamma),
            error=None,
        )

    @staticmethod
    def generate_more_sums_than_differences_seed() -> list[int]:
        """Returns known MSTD construction seed (e.g. Hegarty/Martin-O'Bryant seed)."""
        return [0, 2, 3, 4, 7, 11, 12, 14]
