from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class RawProduct:
    """Common shape every scraper implementation must produce.

    Keeping this contract identical between sources is what makes the
    scraper pluggable - the pipeline never needs to know which one ran.
    """

    external_id: str
    name: str
    source: str
    category: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    shop_name: Optional[str] = None
    shop_id: Optional[str] = None
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    units_sold: Optional[int] = None
    revenue: Optional[float] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    commission_rate: Optional[float] = None
    video_count: Optional[int] = None


class BaseScraper(ABC):
    @abstractmethod
    async def search_products(self, keyword: str, limit: int = 20) -> List[RawProduct]:
        """Search TikTok Shop for products matching `keyword`."""
        raise NotImplementedError
