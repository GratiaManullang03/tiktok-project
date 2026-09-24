import math
from dataclasses import dataclass
from typing import Optional

from app.core.config import settings

# ponytail: heuristic reference point, not a measured benchmark - tune once
# real sales-velocity data is available.
VELOCITY_REFERENCE_UNITS_PER_DAY = 50.0

# ponytail: search-result counts at/above this score 0 on competition (log scale).
# Heuristic - popular keywords like "serum" return ~300k results.
COMPETITION_REFERENCE_RESULTS = 1_000_000

# Tokopedia ratings cluster at 4.7-4.9, so a plain /5 scale barely separates products.
# Anything at or below the floor scores 0.
RATING_FLOOR = 4.0


@dataclass
class ScoreInput:
    # Units sold per day between the two newest snapshots, and between the 2nd/3rd newest.
    # None when there aren't enough snapshots yet.
    recent_velocity: Optional[float]
    previous_velocity: Optional[float]
    rating: Optional[float]
    # Total search results for the keyword the product was found under.
    competitor_count: Optional[int]


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
        if not data.recent_velocity:
            return 0.0
        return min(data.recent_velocity / VELOCITY_REFERENCE_UNITS_PER_DAY * 100, 100.0)

    def _growth_score(self, data: ScoreInput) -> float:
        if data.previous_velocity is None or data.recent_velocity is None:
            return 0.0
        if data.previous_velocity == 0:
            return 100.0 if data.recent_velocity > 0 else 0.0
        growth = (data.recent_velocity - data.previous_velocity) / data.previous_velocity
        return max(min(growth * 100, 100.0), 0.0)

    def _rating_score(self, data: ScoreInput) -> float:
        if not data.rating:
            return 0.0
        return max(min((data.rating - RATING_FLOOR) / (5.0 - RATING_FLOOR) * 100, 100.0), 0.0)

    def _competition_score(self, data: ScoreInput) -> float:
        if data.competitor_count is None:
            return 0.0
        ratio = math.log10(1 + data.competitor_count) / math.log10(1 + COMPETITION_REFERENCE_RESULTS)
        return max(100.0 * (1 - ratio), 0.0)
