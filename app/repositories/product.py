from typing import Optional, List, Tuple
import psycopg2.extras

from app.repositories.base import BaseRepository

TABLE = "tiktok.mst_product"


class ProductRepository(BaseRepository):
    def __init__(self):
        super().__init__(table=TABLE, pk_column="mp_id")

    def get(self, db, id_: int) -> Optional[psycopg2.extras.RealDictRow]:
        """Overrides BaseRepository.get - soft-deleted products are invisible via the API."""
        with db.cursor() as cur:
            cur.execute(
                f"SELECT * FROM {TABLE} WHERE mp_id = %(id)s AND is_deleted = FALSE",
                {"id": id_},
            )
            return cur.fetchone()

    def get_by_external_id(self, db, external_id: str) -> Optional[psycopg2.extras.RealDictRow]:
        """Used by the scraper upsert - matches regardless of is_deleted (dedup by identity)."""
        with db.cursor() as cur:
            cur.execute(
                f"SELECT * FROM {TABLE} WHERE mp_external_id = %(external_id)s",
                {"external_id": external_id},
            )
            return cur.fetchone()

    def list_with_latest_score(
        self,
        db,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> Tuple[List[psycopg2.extras.RealDictRow], int]:
        """Products joined with their latest total score, sorted score-desc."""
        conditions = ["p.is_deleted = FALSE"]
        params: dict = {}
        if category:
            conditions.append("p.mp_category = %(category)s")
            params["category"] = category
        if keyword:
            conditions.append("p.mp_name ILIKE %(keyword)s")
            params["keyword"] = f"%{keyword}%"
        where_clause = f"WHERE {' AND '.join(conditions)}"

        base_query = f"""
            FROM {TABLE} p
            LEFT JOIN LATERAL (
                SELECT hps_total_score
                FROM tiktok.his_product_score
                WHERE hps_mp_id = p.mp_id
                ORDER BY created_at DESC
                LIMIT 1
            ) s ON true
            {where_clause}
        """

        with db.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS count {base_query}", params)
            total = cur.fetchone()["count"]

            cur.execute(
                f"SELECT p.*, s.hps_total_score AS latest_score {base_query} "
                f"ORDER BY s.hps_total_score DESC NULLS LAST "
                f"OFFSET %(skip)s LIMIT %(limit)s",
                {**params, "skip": skip, "limit": limit},
            )
            rows = cur.fetchall()
        return rows, total

    def count_active_in_category(self, db, category: Optional[str], exclude_product_id: int) -> int:
        """Number of other active products in the same category - used as a competition signal."""
        if not category:
            return 0
        with db.cursor() as cur:
            cur.execute(
                f"SELECT COUNT(*) AS count FROM {TABLE} "
                f"WHERE mp_category = %(category)s AND is_active = TRUE "
                f"AND is_deleted = FALSE AND mp_id != %(exclude_id)s",
                {"category": category, "exclude_id": exclude_product_id},
            )
            return cur.fetchone()["count"]

    def soft_delete(self, db, product_id: int) -> Optional[psycopg2.extras.RealDictRow]:
        """Does not commit - caller owns the transaction boundary."""
        with db.cursor() as cur:
            cur.execute(
                f"UPDATE {TABLE} SET is_deleted = TRUE, deleted_at = now() "
                f"WHERE mp_id = %(id)s AND is_deleted = FALSE RETURNING *",
                {"id": product_id},
            )
            return cur.fetchone()
