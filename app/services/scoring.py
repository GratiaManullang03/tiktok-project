from dataclasses import dataclass
from typing import Optional

from app.core.config import settings

# ponytail: heuristic reference point, not a measured benchmark - tune once
# real sales-velocity data is available.
VELOCITY_REFERENCE_UNITS_PER_DAY = 50.0


@dataclass
class ScoreInput:
    units_sold: Optional[int]
    days_since_first_seen: int
    previous_units_sold: Optional[int]
    rating: Optional[float]
    competitor_count: int


@dataclass
class ScoreBreakdown:
    total_score: float
    sales_velocity_score: float
    growth_score: float
    rating_score: float
    competition_score: float


class ProductScoringService:
    """Deterministic, explainable scoring - no LLM involved.

    Each component is normalized to 0-100, then combined with configurable
    weights so the formula can be tuned without touching this logic.
    """

    def __init__(self):
        self.weights = {
            "sales_velocity": settings.SCORE_WEIGHT_SALES_VELOCITY,
            "growth": settings.SCORE_WEIGHT_GROWTH,
            "rating": settings.SCORE_WEIGHT_RATING,
            "competition": settings.SCORE_WEIGHT_COMPETITION,
        }

    def compute(self, data: ScoreInput) -> ScoreBreakdown:
        sales_velocity_score = self._sales_velocity_score(data)
        growth_score = self._growth_score(data)
        rating_score = self._rating_score(data)
        competition_score = self._competition_score(data)

        total_score = (
            sales_velocity_score * self.weights["sales_velocity"]
            + growth_score * self.weights["growth"]
            + rating_score * self.weights["rating"]
            + competition_score * self.weights["competition"]
        )

        return ScoreBreakdown(
            total_score=round(total_score, 2),
            sales_velocity_score=round(sales_velocity_score, 2),
            growth_score=round(growth_score, 2),
            rating_score=round(rating_score, 2),
            competition_score=round(competition_score, 2),
        )

    def _sales_velocity_score(self, data: ScoreInput) -> float:
        if not data.units_sold:
            return 0.0
        days = max(data.days_since_first_seen, 1)
        velocity = data.units_sold / days
        return min(velocity / VELOCITY_REFERENCE_UNITS_PER_DAY * 100, 100.0)

    def _growth_score(self, data: ScoreInput) -> float:
        if data.previous_units_sold is None or data.units_sold is None:
            return 0.0
        if data.previous_units_sold == 0:
            return 100.0 if data.units_sold > 0 else 0.0
        growth = (data.units_sold - data.previous_units_sold) / data.previous_units_sold
        return max(min(growth * 100, 100.0), 0.0)

    def _rating_score(self, data: ScoreInput) -> float:
        if not data.rating:
            return 0.0
        return min(data.rating / 5.0 * 100, 100.0)

    def _competition_score(self, data: ScoreInput) -> float:
        return 100.0 / (1 + data.competitor_count)
