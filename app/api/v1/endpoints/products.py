from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from psycopg2.extensions import connection as Connection

from app.db.session import get_db
from app.repositories.product import ProductRepository
from app.repositories.score import ScoreRepository
from app.repositories.analysis import AnalysisRepository
from app.schemas.product import Product, ProductListItem, ProductDetail, ProductReplace, ProductPatch
from app.schemas.score import ProductScore
from app.schemas.analysis import ProductAnalysis
from app.schemas.common import DataResponse, PaginationResponse
from app.services.pipeline import analyze_product

router = APIRouter()
product_repo = ProductRepository()
score_repo = ScoreRepository()
analysis_repo = AnalysisRepository()


@router.get("/", response_model=PaginationResponse[ProductListItem])
def get_products(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    category: Optional[str] = None,
    keyword: Optional[str] = None,
    db: Connection = Depends(get_db),
):
    """List products with their latest score, sorted highest score first."""
    skip = (page - 1) * per_page
    rows, total = product_repo.list_with_latest_score(
        db, skip=skip, limit=per_page, category=category, keyword=keyword
    )
    items = [ProductListItem.model_validate(row) for row in rows]

    return PaginationResponse.build(
        message="Products retrieved successfully",
        data=items,
        page=page,
        per_page=per_page,
        total=total,
    )


@router.get("/{product_id}", response_model=DataResponse[ProductDetail])
def get_product(product_id: int, db: Connection = Depends(get_db)):
    """Product detail: latest score breakdown + latest LLM analysis, if any. Not paginated - single resource."""
    product = product_repo.get(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    latest_score = score_repo.get_latest(db, product_id)
    latest_analysis = analysis_repo.get_latest(db, product_id)

    detail = ProductDetail(
        **Product.model_validate(product).model_dump(),
        latest_score=ProductScore.model_validate(latest_score) if latest_score else None,
        latest_analysis=ProductAnalysis.model_validate(latest_analysis) if latest_analysis else None,
    )

    return DataResponse(success=True, message="Product retrieved successfully", data=detail)


@router.put("/{product_id}", response_model=DataResponse[Product])
def replace_product(product_id: int, body: ProductReplace, db: Connection = Depends(get_db)):
    """Full replace - every editable field is required and gets overwritten."""
    if not product_repo.get(db, product_id):
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        updated = product_repo.update(db, product_id, body.model_dump())
        db.commit()
    except Exception:
        db.rollback()
        raise

    return DataResponse(
        success=True,
        message="Product replaced successfully",
        data=Product.model_validate(updated),
    )


@router.patch("/{product_id}", response_model=DataResponse[Product])
def patch_product(product_id: int, body: ProductPatch, db: Connection = Depends(get_db)):
    """Partial update - only the fields provided in the request body get changed."""
    if not product_repo.get(db, product_id):
        raise HTTPException(status_code=404, detail="Product not found")

    fields = body.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    try:
        updated = product_repo.update(db, product_id, fields)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return DataResponse(
        success=True,
        message="Product updated successfully",
        data=Product.model_validate(updated),
    )


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, db: Connection = Depends(get_db)):
    """Soft delete - flips is_deleted/deleted_at, keeps score/analysis history intact."""
    if not product_repo.get(db, product_id):
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        product_repo.soft_delete(db, product_id)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return Response(status_code=204)


@router.post("/{product_id}/analyze", response_model=DataResponse[ProductAnalysis])
def trigger_analysis(product_id: int, db: Connection = Depends(get_db)):
    """Run LLM analysis for one product now (synchronous - Groq is fast)."""
    product = product_repo.get(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    analysis = analyze_product(db, product_id)
    return DataResponse(
        success=True,
        message="Analysis generated successfully",
        data=ProductAnalysis.model_validate(analysis),
    )
