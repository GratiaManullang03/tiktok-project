from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

JobStatus = Literal["pending", "running", "done", "partial", "failed"]


class ScrapeRunRequest(BaseModel):
    keyword: str
    limit: int = Field(default=20, ge=1, le=100)


class ScrapeJob(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tsj_id: int
    tsj_keyword: str
    tsj_source: str
    tsj_status: JobStatus
    tsj_limit: Optional[int] = None
    tsj_finished_at: Optional[datetime] = None
    tsj_products_found: Optional[int] = None
    tsj_error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
