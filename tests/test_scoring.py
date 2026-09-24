from app.services.scoring import ProductScoringService, ScoreInput


def test_scoring_caps_all_components_at_100():
    service = ProductScoringService()
    result = service.compute(
        ScoreInput(recent_velocity=500.0, previous_velocity=100.0, rating=5.0, competitor_count=0)
    )
    assert result.sales_velocity_score == 100.0
    assert result.growth_score == 100.0
    assert result.rating_score == 100.0
    assert result.competition_score == 100.0
    assert result.total_score == 100.0


def test_scoring_missing_data_defaults_components_to_zero():
    service = ProductScoringService()
    result = service.compute(
        ScoreInput(recent_velocity=None, previous_velocity=None, rating=None, competitor_count=None)
    )
    assert result.total_score == 0.0


def test_rating_scale_separates_typical_ratings():
    service = ProductScoringService()
    score = lambda r: service.compute(ScoreInput(None, None, r, None)).rating_score
    assert score(4.5) == 50.0
    assert score(4.9) > score(4.7)
    assert score(3.5) == 0.0


def test_competition_drops_on_log_scale():
    service = ProductScoringService()
    score = lambda n: service.compute(ScoreInput(None, None, None, n)).competition_score
    assert score(999) == 50.0  # log10(1000) / log10(~1M) = 0.5
    assert score(300_000) < score(1_000) < score(10)
    assert score(5_000_000) == 0.0
