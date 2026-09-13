from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.schemas.score import ProductScore
from app.schemas.analysis import ProductAnalysis


class ProductBase(BaseModel):
    mp_external_id: str
    mp_name: str
    mp_category: Optional[str] = None
    mp_price: Optional[float] = None
    mp_currency: Optional[str] = None
    mp_shop_name: Optional[str] = None
    mp_shop_id: Optional[str] = None
    mp_image_url: Optional[str] = None
    mp_product_url: Optional[str] = None
    mp_source: str


class Product(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    mp_id: int
    mp_last_scraped_at: datetime
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class ProductListItem(Product):
    """Product row enriched with its latest score, used for the list endpoint."""

    latest_score: Optional[float] = None


class ProductDetail(Product):
    """Full product detail: latest score breakdown + latest analysis, if any."""

    latest_score: Optional[ProductScore] = None
    latest_analysis: Optional[ProductAnalysis] = None


class ProductReplace(BaseModel):
    """PUT /products/{id} - every editable field is required, replaces the whole resource."""

    mp_name: str
    mp_category: Optional[str] = None
    mp_price: Optional[float] = None
    mp_currency: Optional[str] = None
    mp_shop_name: Optional[str] = None
    mp_shop_id: Optional[str] = None
    mp_image_url: Optional[str] = None
    mp_product_url: Optional[str] = None
    is_active: bool


class ProductPatch(BaseModel):
    """PATCH /products/{id} - every field optional, only what's set gets updated."""

    mp_name: Optional[str] = None
    mp_category: Optional[str] = None
    mp_price: Optional[float] = None
    mp_currency: Optional[str] = None
    mp_shop_name: Optional[str] = None
    mp_shop_id: Optional[str] = None
    mp_image_url: Optional[str] = None
    mp_product_url: Optional[str] = None
    is_active: Optional[bool] = None
