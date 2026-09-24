"""Re-run scrape jobs so products get fresh metric snapshots - velocity needs 2 snapshots,
growth needs 3, so scores only become meaningful with regular rescrapes.

Run with: python scripts/rescrape.py [keyword ...] [--limit N]
No keywords = every keyword scraped before, each with the largest limit it was ever run with.
Schedule it ~daily (snapshots < 20h apart are treated as one), e.g. cron:
  0 7 * * * cd /path/to/tiktok-project && venv/bin/python scripts/rescrape.py
"""
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.session import get_connection  # noqa: E402
from app.repositories.scrape_job import DEFAULT_LIMIT, ScrapeJobRepository  # noqa: E402
from app.services.pipeline import create_scrape_job, run_scrape_job  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("keywords", nargs="*")
parser.add_argument("--limit", type=int, help=f"override every keyword's limit (default: its past max, else {DEFAULT_LIMIT})")
args = parser.parse_args()

job_repo = ScrapeJobRepository()
db = get_connection()
try:
    if args.keywords:
        targets = [(k, args.limit or DEFAULT_LIMIT) for k in args.keywords]
    else:
        targets = [(row["keyword"], args.limit or row["limit"]) for row in job_repo.keywords_with_limit(db)]

    for keyword, limit in targets:
        job = create_scrape_job(db, keyword, limit)
        try:
            run_scrape_job(job["tsj_id"], keyword, limit)
        except Exception as exc:  # noqa: BLE001 - e.g. DB connect failure; keep going with the rest
            # run_scrape_job records its own failures, except when it can't even connect.
            db.rollback()
            job_repo.update(db, job["tsj_id"], {
                "tsj_status": "failed",
                "tsj_finished_at": datetime.now(timezone.utc),
                "tsj_error_message": str(exc),
            })
            db.commit()
        print(f"{keyword} (limit {limit}): {job_repo.get(db, job['tsj_id'])['tsj_status']}")
finally:
    db.close()
