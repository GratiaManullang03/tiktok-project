import re
from typing import List, Optional
import httpx

from app.services.scrapers.base import BaseScraper, RawProduct

SOURCE_NAME = "tokopedia"

SEARCH_URL = "https://gql.tokopedia.com/graphql/SearchProductV5Query"

# ponytail: module-level so it's reused across scraper instances/calls instead of
# opening a new connection pool per search - never explicitly closed, fine for a
# process-lifetime personal tool.
_client = httpx.AsyncClient(timeout=15.0)

_QUERY = """query SearchProductV5Query($params: String!) {
  searchProductV5(params: $params) {
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
        labelGroups { position title __typename }
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

# "80+ terjual", "10rb+ terjual", "500rb+ terjual" - "rb"/"jt" = ribu/juta (thousand/million).
# ponytail: "+" just means "at least this many" on Tokopedia's side - dropped, fine for a
# heuristic sales-velocity signal.
_SOLD_RE = re.compile(r"([\d]+(?:[.,]\d+)?)\s*(rb|jt)?\+?\s*terjual", re.IGNORECASE)
_SOLD_MULTIPLIER = {"rb": 1_000, "jt": 1_000_000}


class TokopediaScraper(BaseScraper):
    """Fetches products via Tokopedia's public search API - no browser, no API key.

    Indonesia's TikTok Shop catalog merged into Tokopedia in 2023 (products carry a
    linked `ttsProductID`), so this reaches the same product data through a public,
    unauthenticated GraphQL endpoint instead of TikTok's own captcha-walled shop domain.
    """

    async def search_products(self, keyword: str, limit: int = 20) -> List[RawProduct]:
        params = (
            f"device=desktop&l_name=sre&q={keyword}&rows={limit}"
            f"&safe_search=false&scheme=https&source=search&st=product&start=0"
        )
        payload = [{
            "operationName": "SearchProductV5Query",
            "variables": {"params": params},
            "query": _QUERY,
        }]
        response = await _client.post(SEARCH_URL, json=payload, headers=_HEADERS)
        response.raise_for_status()
        body = response.json()
        result = body[0] if isinstance(body, list) else body
        products = result["data"]["searchProductV5"]["data"]["products"]
        parsed = (self._parse_item(item) for item in products[:limit])
        return [p for p in parsed if p is not None]

    def _parse_item(self, item: dict) -> Optional[RawProduct]:
        external_id = item.get("id")
        if external_id is None:
            return None

        shop = item.get("shop") or {}
        rating = item.get("rating")
        return RawProduct(
            external_id=str(external_id),
            name=item.get("name", ""),
            source=SOURCE_NAME,
            category=(item.get("category") or {}).get("name"),
            price=(item.get("price") or {}).get("number"),
            currency="IDR",
            shop_name=shop.get("name"),
            shop_id=str(shop["id"]) if shop.get("id") is not None else None,
            image_url=(item.get("mediaURL") or {}).get("image"),
            product_url=item.get("url"),
            units_sold=self._parse_units_sold(item.get("labelGroups")),
            rating=float(rating) if rating else None,
        )

    @staticmethod
    def _parse_units_sold(label_groups: Optional[list]) -> Optional[int]:
        for label in label_groups or []:
            if label.get("position") != "ri_product_credibility":
                continue
            match = _SOLD_RE.search(label.get("title", ""))
            if not match:
                return None
            number = float(match.group(1).replace(",", "."))
            multiplier = _SOLD_MULTIPLIER.get((match.group(2) or "").lower(), 1)
            return int(number * multiplier)
        return None
