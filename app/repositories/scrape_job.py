from app.repositories.base import BaseRepository

TABLE = "tiktok.trx_scrape_job"


class ScrapeJobRepository(BaseRepository):
    def __init__(self):
        super().__init__(table=TABLE, pk_column="tsj_id")
