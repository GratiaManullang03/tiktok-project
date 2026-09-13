from typing import Optional
import psycopg2.extras

from app.repositories.base import BaseRepository

TABLE = "tiktok.his_product_analysis"


class AnalysisRepository(BaseRepository):
    def __init__(self):
        super().__init__(table=TABLE, pk_column="hpa_id")

    def get_latest(self, db, product_id: int) -> Optional[psycopg2.extras.RealDictRow]:
        with db.cursor() as cur:
            cur.execute(
                f"SELECT * FROM {TABLE} WHERE hpa_mp_id = %(product_id)s "
                f"ORDER BY created_at DESC LIMIT 1",
                {"product_id": product_id},
            )
            return cur.fetchone()
