from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict

Verdict = Literal["buy", "watch", "avoid"]


class AnalysisResult(BaseModel):
    """Structured output expected back from the LLM."""

    summary: str
    strengths: List[str]
    risks: List[str]
    target_audience: str
    marketing_angle: str
    verdict: Verdict


class ProductAnalysis(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hpa_id: int
    hpa_mp_id: int
    hpa_llm_model: str
    hpa_summary: str
    hpa_strengths: List[str]
    hpa_risks: List[str]
    hpa_target_audience: str
    hpa_marketing_angle: str
    hpa_verdict: str
    hpa_raw_response: Optional[dict] = None
    created_at: datetime
