from typing import List

from app.repositories.base import BaseRepository

TABLE = "tiktok.trx_scrape_job"

# Jobs created before tsj_limit existed have NULL - fall back to the API default.
DEFAULT_LIMIT = 20


class ScrapeJobRepository(BaseRepository):
    def __init__(self):
        super().__init__(table=TABLE, pk_column="tsj_id")

    def keywords_with_limit(self, db) -> List[dict]:
        """Every keyword scraped before, with the largest limit it was ever scraped with."""
        with db.cursor() as cur:
            cur.execute(
                f"SELECT tsj_keyword AS keyword, COALESCE(MAX(tsj_limit), %(default)s) AS limit "
                f"FROM {TABLE} GROUP BY tsj_keyword ORDER BY tsj_keyword",
                {"default": DEFAULT_LIMIT},
            )
            return cur.fetchall()
