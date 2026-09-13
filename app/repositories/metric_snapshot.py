from typing import List
import psycopg2.extras

from app.repositories.base import BaseRepository

TABLE = "tiktok.his_product_metric"


class MetricSnapshotRepository(BaseRepository):
    def __init__(self):
        super().__init__(table=TABLE, pk_column="hpm_id")

    def get_latest(self, db, product_id: int, n: int = 2) -> List[psycopg2.extras.RealDictRow]:
        """Most recent `n` snapshots for a product, newest first."""
        with db.cursor() as cur:
            cur.execute(
                f"SELECT * FROM {TABLE} WHERE hpm_mp_id = %(product_id)s "
                f"ORDER BY created_at DESC LIMIT %(n)s",
                {"product_id": product_id, "n": n},
            )
            return cur.fetchall()
