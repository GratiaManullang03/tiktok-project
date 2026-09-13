from fastapi import APIRouter, Depends
from psycopg2.extensions import connection as Connection

from app.db.session import get_db
from app.schemas.common import ResponseBase

router = APIRouter()


@router.get("/", response_model=ResponseBase)
async def health_check(db: Connection = Depends(get_db)):
    """Health check endpoint"""
    try:
        with db.cursor() as cur:
            cur.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:  # noqa: BLE001 - reported in the response, not raised
        db_status = f"unhealthy ({e})"

    return ResponseBase(success=True, message=f"Database: {db_status}")
