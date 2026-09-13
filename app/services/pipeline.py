from datetime import datetime, timezone
import psycopg2.extras

from app.db.session import get_connection
from app.repositories.product import ProductRepository
from app.repositories.metric_snapshot import MetricSnapshotRepository
from app.repositories.score import ScoreRepository
from app.repositories.analysis import AnalysisRepository
from app.repositories.scrape_job import ScrapeJobRepository
from app.services.scrapers.tokopedia_scraper import TokopediaScraper
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


async def run_scrape_job(job_id: int, keyword: str, limit: int) -> None:
    """Full pipeline: scrape -> upsert product + metrics -> score. Runs as a background task
    with its own DB connection, since it outlives the original request."""
    db = get_connection()
    try:
        job_repo.update(db, job_id, {"tsj_status": "running"})
        db.commit()

        raw_products = await scraper.search_products(keyword, limit)

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
            "hpm_review_count": raw.review_count,
            "hpm_commission_rate": raw.commission_rate,
            "hpm_video_count": raw.video_count,
        },
    )


def score_product(db, product_id: int) -> psycopg2.extras.RealDictRow:
    """Recompute and persist the score for one product from its latest metrics.
    Part of the caller's transaction - does not commit."""
    product = product_repo.get(db, product_id)
    snapshots = metric_repo.get_latest(db, product_id, n=2)
    latest = snapshots[0] if snapshots else None
    previous = snapshots[1] if len(snapshots) > 1 else None

    days_since_first_seen = (datetime.now(timezone.utc) - product["created_at"]).days
    competitor_count = product_repo.count_active_in_category(
        db, product["mp_category"], product["mp_id"]
    )

    breakdown = scoring_service.compute(
        ScoreInput(
            units_sold=latest["hpm_units_sold"] if latest else None,
            days_since_first_seen=days_since_first_seen,
            previous_units_sold=previous["hpm_units_sold"] if previous else None,
            rating=float(latest["hpm_rating"]) if latest and latest["hpm_rating"] is not None else None,
            competitor_count=competitor_count,
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

        result = analysis_service.analyze(product, breakdown)

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
