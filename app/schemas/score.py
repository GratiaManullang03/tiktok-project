from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ProductScore(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hps_id: int
    hps_mp_id: int
    hps_total_score: float
    hps_sales_velocity_score: float
    hps_growth_score: float
    hps_rating_score: float
    hps_competition_score: float
    created_at: datetime
