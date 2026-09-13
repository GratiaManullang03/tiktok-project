from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from psycopg2.extensions import connection as Connection

from app.db.session import get_db
from app.repositories.scrape_job import ScrapeJobRepository
from app.schemas.scrape_job import ScrapeRunRequest, ScrapeJob
from app.schemas.common import DataResponse, PaginationResponse
from app.services.pipeline import run_scrape_job
from app.services.scrapers.tokopedia_scraper import SOURCE_NAME

router = APIRouter()
job_repo = ScrapeJobRepository()


@router.post("/run", response_model=DataResponse[ScrapeJob])
def run_scrape(
    request: ScrapeRunRequest,
    background_tasks: BackgroundTasks,
    db: Connection = Depends(get_db),
):
    """Kick off a scrape job in the background and return its id immediately."""
    job = job_repo.create(
        db,
        {
            "tsj_keyword": request.keyword,
            "tsj_source": SOURCE_NAME,
            "tsj_status": "pending",
        },
    )
    db.commit()
    background_tasks.add_task(run_scrape_job, job["tsj_id"], request.keyword, request.limit)

    return DataResponse(
        success=True,
        message="Scrape job started",
        data=ScrapeJob.model_validate(job),
    )


@router.get("/jobs/{job_id}", response_model=DataResponse[ScrapeJob])
def get_scrape_job(job_id: int, db: Connection = Depends(get_db)):
    """Not paginated - single resource."""
    job = job_repo.get(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scrape job not found")

    return DataResponse(success=True, message="Job retrieved successfully", data=ScrapeJob.model_validate(job))


@router.get("/jobs", response_model=PaginationResponse[ScrapeJob])
def list_scrape_jobs(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: Connection = Depends(get_db),
):
    skip = (page - 1) * per_page
    jobs = job_repo.get_multi(db, skip=skip, limit=per_page)
    total = job_repo.count(db)

    return PaginationResponse.build(
        message="Jobs retrieved successfully",
        data=[ScrapeJob.model_validate(job) for job in jobs],
        page=page,
        per_page=per_page,
        total=total,
    )
