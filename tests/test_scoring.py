from app.services.scoring import ProductScoringService, ScoreInput


def test_scoring_caps_all_components_at_100():
    service = ProductScoringService()
    result = service.compute(
        ScoreInput(
            units_sold=1000,
            days_since_first_seen=10,
            previous_units_sold=500,
            rating=5.0,
            competitor_count=0,
        )
    )
    assert result.sales_velocity_score == 100.0
    assert result.growth_score == 100.0
    assert result.rating_score == 100.0
    assert result.competition_score == 100.0
    assert result.total_score == 100.0


def test_scoring_missing_data_defaults_components_to_zero():
    service = ProductScoringService()
    result = service.compute(
        ScoreInput(
            units_sold=None,
            days_since_first_seen=5,
            previous_units_sold=None,
            rating=None,
            competitor_count=5,
        )
    )
    assert result.sales_velocity_score == 0.0
    assert result.growth_score == 0.0
    assert result.rating_score == 0.0
    assert result.competition_score == round(100 / 6, 2)
    assert result.total_score == round(result.competition_score * service.weights["competition"], 2)
