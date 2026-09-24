from datetime import datetime, timedelta, timezone
from typing import Optional
import psycopg2.extras

from app.db.session import get_connection
from app.repositories.product import ProductRepository
from app.repositories.metric_snapshot import MetricSnapshotRepository
from app.repositories.score import ScoreRepository
from app.repositories.analysis import AnalysisRepository
from app.repositories.scrape_job import ScrapeJobRepository
from app.services.scrapers.tokopedia_scraper import TokopediaScraper, SOURCE_NAME
from app.services.scrapers.base import RawProduct
from app.services.scoring import ProductScoringService, ScoreInput, ScoreBreakdown
from app.services.llm_analysis import GroqAnalysisService

product_repo = ProductRepository()
metric_repo = MetricSnapshotRepository()
score_repo = ScoreRepository()
analysis_repo = AnalysisRepository()
job_repo = ScrapeJobRepository()
scoring_service = ProductScoringService()
analysis_service = GroqAnalysisService()
scraper = TokopediaScraper()

# Snapshots closer together than this are treated as the same observation - a product found
# under two keywords in one rescrape run, or a manual scrape on top of the daily cron, would
# otherwise yield a near-zero sales delta.
MIN_SNAPSHOT_GAP = timedelta(hours=20)
# ponytail: how many recent snapshots to scan for spaced-out ones; plenty for daily rescrapes,
# raise it if a product gets scraped many times a day.
SNAPSHOT_WINDOW = 30


def create_scrape_job(db, keyword: str, limit: int) -> psycopg2.extras.RealDictRow:
    """Insert a pending job row and commit, so it's visible before the background run starts."""
    job = job_repo.create(
        db,
        {"tsj_keyword": keyword, "tsj_limit": limit, "tsj_source": SOURCE_NAME, "tsj_status": "pending"},
    )
    db.commit()
    return job


def run_scrape_job(job_id: int, keyword: str, limit: int) -> None:
    """Full pipeline: scrape -> upsert product + metrics -> score. Runs as a background task
    with its own DB connection, since it outlives the original request. Plain `def` on purpose:
    FastAPI runs sync background tasks in a threadpool, so the blocking psycopg2/httpx calls
    don't stall the event loop."""
    db = get_connection()
    try:
        job_repo.update(db, job_id, {"tsj_status": "running"})
        db.commit()

        raw_products = scraper.search_products(keyword, limit)

        products_found = 0
        errors: list[str] = []
        for raw in raw_products:
            try:
                product = _upsert_product(db, raw)
                _save_metric_snapshot(db, product["mp_id"], raw)
                score_product(db, product["mp_id"])
                db.commit()
                products_found += 1
            except Exception as exc:  # noqa: BLE001 - one bad product shouldn't fail the whole job
                db.rollback()
                errors.append(f"{raw.external_id}: {exc}")

        status = "done" if not errors else ("failed" if products_found == 0 else "partial")
        job_repo.update(
            db,
            job_id,
            {
                "tsj_status": status,
                "tsj_finished_at": datetime.now(timezone.utc),
                "tsj_products_found": products_found,
                "tsj_error_message": "; ".join(errors) if errors else None,
            },
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001 - surfaced via job row, not re-raised (background task)
        db.rollback()
        job_repo.update(
            db,
            job_id,
            {
                "tsj_status": "failed",
                "tsj_finished_at": datetime.now(timezone.utc),
                "tsj_error_message": str(exc),
            },
        )
        db.commit()
    finally:
        db.close()


def _upsert_product(db, raw: RawProduct) -> psycopg2.extras.RealDictRow:
    """Part of the caller's transaction - does not commit."""
    existing = product_repo.get_by_external_id(db, raw.external_id)
    fields = {
        "mp_external_id": raw.external_id,
        "mp_name": raw.name,
        "mp_category": raw.category,
        "mp_price": raw.price,
        "mp_currency": raw.currency,
        "mp_shop_name": raw.shop_name,
        "mp_shop_id": raw.shop_id,
        "mp_image_url": raw.image_url,
        "mp_product_url": raw.product_url,
        "mp_source": raw.source,
        "mp_last_scraped_at": datetime.now(timezone.utc),
        "is_deleted": False,
        "deleted_at": None,
    }
    if existing:
        return product_repo.update(db, existing["mp_id"], fields)
    return product_repo.create(db, fields)


def _save_metric_snapshot(db, product_id: int, raw: RawProduct) -> None:
    """Part of the caller's transaction - does not commit."""
    metric_repo.create(
        db,
        {
            "hpm_mp_id": product_id,
            "hpm_units_sold": raw.units_sold,
            "hpm_revenue": raw.revenue,
            "hpm_rating": raw.rating,
            "hpm_competitor_count": raw.competitor_count,
        },
    )


def _spaced_snapshots(snapshots: list) -> list:
    """Newest snapshot, then each next one at least MIN_SNAPSHOT_GAP older than the last pick.
    `snapshots` is newest first."""
    picked = []
    for snap in snapshots:
        if not picked or picked[-1]["created_at"] - snap["created_at"] >= MIN_SNAPSHOT_GAP:
            picked.append(snap)
    return picked


def _units_per_day(newer, older) -> Optional[float]:
    """Sales rate between two snapshots. `hpm_units_sold` is a lifetime total, so only the
    delta between snapshots says how fast a product is selling *now*."""
    if newer is None or older is None:
        return None
    if newer["hpm_units_sold"] is None or older["hpm_units_sold"] is None:
        return None
    days = (newer["created_at"] - older["created_at"]).total_seconds() / 86400
    return max(newer["hpm_units_sold"] - older["hpm_units_sold"], 0) / days


def score_product(db, product_id: int) -> psycopg2.extras.RealDictRow:
    """Recompute and persist the score for one product from its latest metrics.
    Velocity needs 2 snapshots >= MIN_SNAPSHOT_GAP apart, growth needs 3 - until then those
    components score 0. Part of the caller's transaction - does not commit."""
    recent = metric_repo.get_latest(db, product_id, n=SNAPSHOT_WINDOW)
    s0, s1, s2 = (_spaced_snapshots(recent) + [None, None, None])[:3]

    # competitor_count belongs to the keyword a snapshot was scraped under, not the product.
    # Taking the minimum across recent snapshots (the narrowest niche it ranks in) keeps the
    # score from flipping with whichever keyword happened to run last.
    competitor_counts = [s["hpm_competitor_count"] for s in recent if s["hpm_competitor_count"] is not None]

    breakdown = scoring_service.compute(
        ScoreInput(
            recent_velocity=_units_per_day(s0, s1),
            previous_velocity=_units_per_day(s1, s2),
            rating=float(s0["hpm_rating"]) if s0 and s0["hpm_rating"] is not None else None,
            competitor_count=min(competitor_counts) if competitor_counts else None,
        )
    )

    return score_repo.create(
        db,
        {
            "hps_mp_id": product_id,
            "hps_total_score": breakdown.total_score,
            "hps_sales_velocity_score": breakdown.sales_velocity_score,
            "hps_growth_score": breakdown.growth_score,
            "hps_rating_score": breakdown.rating_score,
            "hps_competition_score": breakdown.competition_score,
        },
    )


def analyze_product(db, product_id: int) -> psycopg2.extras.RealDictRow:
    """Trigger LLM analysis for one product using its latest score. Synchronous - Groq is fast.
    Commits on success, rolls back on failure (score_product may have written a new score row)."""
    try:
        product = product_repo.get(db, product_id)
        score = score_repo.get_latest(db, product_id)
        if score is None:
            score = score_product(db, product_id)

        breakdown = ScoreBreakdown(
            total_score=float(score["hps_total_score"]),
            sales_velocity_score=float(score["hps_sales_velocity_score"]),
            growth_score=float(score["hps_growth_score"]),
            rating_score=float(score["hps_rating_score"]),
            competition_score=float(score["hps_competition_score"]),
        )

        latest_metrics = metric_repo.get_latest(db, product_id, n=1)
        result = analysis_service.analyze(product, breakdown, latest_metrics[0] if latest_metrics else None)

        analysis = analysis_repo.create(
            db,
            {
                "hpa_mp_id": product_id,
                "hpa_llm_model": analysis_service.model,
                "hpa_summary": result.summary,
                "hpa_strengths": result.strengths,
                "hpa_risks": result.risks,
                "hpa_target_audience": result.target_audience,
                "hpa_marketing_angle": result.marketing_angle,
                "hpa_verdict": result.verdict,
                "hpa_raw_response": result.model_dump(),
            },
        )
        db.commit()
        return analysis
    except Exception:
        db.rollback()
        raise
