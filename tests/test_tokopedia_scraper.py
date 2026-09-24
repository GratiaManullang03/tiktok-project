import pytest

from app.services.scrapers import tokopedia_scraper
from app.services.scrapers.tokopedia_scraper import TokopediaScraper


def _fake_post(monkeypatch, body, sent=None):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return body

    def fake_post(url, json, headers):
        if sent is not None:
            sent["params"] = json[0]["variables"]["params"]
        return FakeResponse()

    monkeypatch.setattr(tokopedia_scraper._client, "post", fake_post)


def test_search_encodes_keyword_and_reads_exact_sold(monkeypatch):
    sent = {}
    _fake_post(monkeypatch, [{"data": {"searchProductV5": {
        "header": {"totalData": 1234},
        "data": {"products": [
            {"id": 1, "name": "Serum", "price": {"number": 10000}, "stock": {"sold": 1462}},
            {"id": 2, "name": "No stock field", "price": {"number": 10000}},
        ]},
    }}}], sent)

    first, second = TokopediaScraper().search_products("serum & toner", limit=5)

    assert "q=serum+%26+toner" in sent["params"]
    assert first.units_sold == 1462
    assert first.revenue == 14_620_000
    assert first.competitor_count == 1234
    assert second.units_sold is None and second.revenue is None


def test_graphql_schema_error_is_reported(monkeypatch):
    _fake_post(monkeypatch, [{"errors": [{"message": "Invalid request schema received."}], "data": None}])
    with pytest.raises(RuntimeError, match="Invalid request schema"):
        TokopediaScraper().search_products("serum")
