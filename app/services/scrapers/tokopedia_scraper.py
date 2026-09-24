from urllib.parse import urlencode
from typing import List, Optional
import httpx

from app.services.scrapers.base import BaseScraper, RawProduct

SOURCE_NAME = "tokopedia"

SEARCH_URL = "https://gql.tokopedia.com/graphql/SearchProductV5Query"

# ponytail: module-level so it's reused across scraper instances/calls instead of
# opening a new connection pool per search - never explicitly closed, fine for a
# process-lifetime personal tool.
_client = httpx.Client(timeout=15.0)

_QUERY = """query SearchProductV5Query($params: String!) {
  searchProductV5(params: $params) {
    header { totalData __typename }
    data {
      products {
        id
        name
        url
        price { number __typename }
        shop { id name __typename }
        rating
        category { name __typename }
        mediaURL { image __typename }
        stock { sold __typename }
        __typename
      }
      __typename
    }
    __typename
  }
}"""

_HEADERS = {
    "content-type": "application/json",
    "accept": "*/*",
    "referer": "https://www.tokopedia.com/",
    "x-source": "tokopedia-lite",
    "x-device": "desktop-0.0",
    "x-tkpd-lite-service": "zeus",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

class TokopediaScraper(BaseScraper):
    """Fetches products via Tokopedia's public search API - no browser, no API key.

    Indonesia's TikTok Shop catalog merged into Tokopedia in 2023 (products carry a
    linked `ttsProductID`), so this reaches the same product data through a public,
    unauthenticated GraphQL endpoint instead of TikTok's own captcha-walled shop domain.
    """

    def search_products(self, keyword: str, limit: int = 20) -> List[RawProduct]:
        params = urlencode({
            "device": "desktop", "l_name": "sre", "q": keyword, "rows": limit,
            "safe_search": "false", "scheme": "https", "source": "search", "st": "product", "start": 0,
        })
        payload = [{
            "operationName": "SearchProductV5Query",
            "variables": {"params": params},
            "query": _QUERY,
        }]
        response = _client.post(SEARCH_URL, json=payload, headers=_HEADERS)
        response.raise_for_status()
        body = response.json()
        result = body[0] if isinstance(body, list) else body
        if not result.get("data"):
            # GraphQL rejects the whole query if any requested field disappears from the schema.
            raise RuntimeError(f"Tokopedia search returned no data: {result.get('errors')}")
        search = result["data"]["searchProductV5"]
        products = search["data"]["products"]
        total_results = (search.get("header") or {}).get("totalData")
        parsed = (self._parse_item(item, total_results) for item in products[:limit])
        return [p for p in parsed if p is not None]

    def _parse_item(self, item: dict, total_results: Optional[int] = None) -> Optional[RawProduct]:
        external_id = item.get("id")
        if external_id is None:
            return None

        shop = item.get("shop") or {}
        rating = item.get("rating")
        price = (item.get("price") or {}).get("number")
        # Exact count only - no fallback to the rounded "10rb+ terjual" label, since mixing the
        # two across snapshots makes the velocity delta meaningless.
        units_sold = (item.get("stock") or {}).get("sold")
        return RawProduct(
            external_id=str(external_id),
            name=item.get("name", ""),
            source=SOURCE_NAME,
            category=(item.get("category") or {}).get("name"),
            price=price,
            currency="IDR",
            shop_name=shop.get("name"),
            shop_id=str(shop["id"]) if shop.get("id") is not None else None,
            image_url=(item.get("mediaURL") or {}).get("image"),
            product_url=item.get("url"),
            units_sold=units_sold,
            # ponytail: lifetime GMV estimate at today's price - ignores past discounts.
            revenue=price * units_sold if price is not None and units_sold is not None else None,
            rating=float(rating) if rating else None,
            competitor_count=total_results,
        )
