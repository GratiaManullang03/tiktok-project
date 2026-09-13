from datetime import datetime, timedelta, timezone

from app.services import pipeline


def test_score_product_wires_metrics_into_expected_breakdown(monkeypatch):
    product = {
        "mp_id": 1,
        "mp_category": "gadget",
        "created_at": datetime.now(timezone.utc) - timedelta(days=10),
    }
    latest = {"hpm_units_sold": 500, "hpm_rating": 4.5}
    previous = {"hpm_units_sold": 250}

    monkeypatch.setattr(pipeline.product_repo, "get", lambda db, id_: product)
    monkeypatch.setattr(
        pipeline.product_repo, "count_active_in_category", lambda db, category, exclude_product_id: 1
    )
    monkeypatch.setattr(pipeline.metric_repo, "get_latest", lambda db, product_id, n=2: [latest, previous])

    created = {}

    def fake_create(db, data):
        created.update(data)
        return data

    monkeypatch.setattr(pipeline.score_repo, "create", fake_create)

    pipeline.score_product(db=None, product_id=1)

    assert created["hps_mp_id"] == 1
    assert created["hps_rating_score"] == 90.0  # 4.5 / 5 * 100
    assert created["hps_competition_score"] == 50.0  # 100 / (1 + 1)
    assert created["hps_total_score"] > 0
