from datetime import datetime, timedelta, timezone

from app.services import pipeline


def _snap(units, days_ago, competitors=999, hours_ago=0):
    return {
        "hpm_units_sold": units,
        "hpm_rating": 4.5,
        "hpm_competitor_count": competitors,
        "created_at": datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hours_ago),
    }


def _score(monkeypatch, snapshots):
    monkeypatch.setattr(pipeline.metric_repo, "get_latest", lambda db, product_id, n: snapshots[:n])
    monkeypatch.setattr(pipeline.score_repo, "create", lambda db, data: data)
    return pipeline.score_product(db=None, product_id=1)


def test_score_product_uses_snapshot_deltas(monkeypatch):
    created = _score(monkeypatch, [_snap(1300, 0), _snap(1200, 4), _snap(1000, 8)])  # newest first

    assert created["hps_mp_id"] == 1
    # 100 units / 4 days = 25/day vs reference 50/day - lifetime total (1300) must not matter
    assert created["hps_sales_velocity_score"] == 50.0
    assert created["hps_growth_score"] == 0.0  # 25/day now vs 50/day before = slowing down
    assert created["hps_rating_score"] == 50.0
    assert created["hps_competition_score"] == 50.0


def test_close_together_snapshots_are_skipped(monkeypatch):
    # Same product scraped twice minutes apart (two keywords in one rescrape run) must not
    # collapse velocity to ~0 - the pair used should be today vs 4 days ago.
    created = _score(monkeypatch, [_snap(1300, 0), _snap(1300, 0, hours_ago=0.1), _snap(1200, 4)])
    assert created["hps_sales_velocity_score"] == 50.0


def test_competition_uses_narrowest_keyword(monkeypatch):
    created = _score(monkeypatch, [_snap(1300, 0, competitors=300_000), _snap(1300, 0, competitors=999, hours_ago=0.1)])
    assert created["hps_competition_score"] == 50.0


def test_single_snapshot_has_no_velocity(monkeypatch):
    created = _score(monkeypatch, [_snap(50_000, 0)])
    assert created["hps_sales_velocity_score"] == 0.0
    assert created["hps_growth_score"] == 0.0
