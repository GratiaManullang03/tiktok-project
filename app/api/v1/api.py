from fastapi import APIRouter

from app.api.v1.endpoints import health, products, scrape

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(scrape.router, prefix="/scrape", tags=["scrape"])
