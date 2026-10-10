from __future__ import annotations

import math
from pydantic import BaseModel, Field


class Circle(BaseModel):
    x: float
    y: float
    r: float = Field(ge=0.0)


class CirclePackingResult(BaseModel):
    is_valid: bool
    num_circles: int
    sum_radii: float
    violations: list[str] = Field(default_factory=list)
    min_pairwise_distance_margin: float = 0.0


class CirclePackingEvaluator:
    """Evaluates circle packing in unit square [0, 1]^2:

    Maximize sum_i r_i subject to:
    r_i <= x_i <= 1 - r_i
    r_i <= y_i <= 1 - r_i
    (x_i - x_j)^2 + (y_i - y_j)^2 >= (r_i + r_j)^2
    """

    @staticmethod
    def evaluate(circles: list[Circle], tolerance: float = 1e-7) -> CirclePackingResult:
        n = len(circles)
        if n == 0:
            return CirclePackingResult(
                is_valid=False,
                num_circles=0,
                sum_radii=0.0,
                violations=["Empty circle configuration."],
            )

        violations: list[str] = []
        min_margin = float("inf")

        for idx, c in enumerate(circles):
            if c.r < 0.0:
                violations.append(f"Circle {idx} has negative radius {c.r}.")
            if c.x - c.r < -tolerance or c.x + c.r > 1.0 + tolerance:
                violations.append(f"Circle {idx} (x={c.x}, r={c.r}) exceeds unit square X bounds.")
            if c.y - c.r < -tolerance or c.y + c.r > 1.0 + tolerance:
                violations.append(f"Circle {idx} (y={c.y}, r={c.r}) exceeds unit square Y bounds.")

        for i in range(n):
            c1 = circles[i]
            for j in range(i + 1, n):
                c2 = circles[j]
                dx = c1.x - c2.x
                dy = c1.y - c2.y
                dist = math.sqrt(dx * dx + dy * dy)
                req_dist = c1.r + c2.r
                margin = dist - req_dist
                if margin < min_margin:
                    min_margin = margin
                if margin < -tolerance:
                    violations.append(
                        f"Overlap between circle {i} and {j}: dist={dist:.7f} < req={req_dist:.7f} (margin={margin:.7e})."
                    )

        sum_r = sum(c.r for c in circles)
        is_valid = len(violations) == 0

        return CirclePackingResult(
            is_valid=is_valid,
            num_circles=n,
            sum_radii=float(sum_r) if is_valid else 0.0,
            violations=violations[:10],
            min_pairwise_distance_margin=float(min_margin) if math.isfinite(min_margin) else 0.0,
        )

    @staticmethod
    def generate_regular_grid(n: int) -> list[Circle]:
        """Generates a valid initial feasible packing grid."""
        grid_dim = math.ceil(math.sqrt(n))
        r = 1.0 / (2.0 * grid_dim)
        circles: list[Circle] = []
        count = 0
        for i in range(grid_dim):
            for j in range(grid_dim):
                if count >= n:
                    break
                cx = (2 * i + 1) * r
                cy = (2 * j + 1) * r
                circles.append(Circle(x=cx, y=cy, r=r * 0.98))
                count += 1
        return circles
