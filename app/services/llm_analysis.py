import json
from groq import Groq
from pydantic import ValidationError

from app.core.config import settings
from app.services.scoring import ScoreBreakdown
from app.schemas.analysis import AnalysisResult

SYSTEM_PROMPT = (
    "You are a TikTok Shop product research analyst. Given product data and a "
    "deterministic score breakdown, respond with ONLY a JSON object with keys: "
    "summary (string), strengths (array of strings), risks (array of strings), "
    "target_audience (string), marketing_angle (string), verdict (one of "
    "'buy', 'watch', 'avoid'). No prose outside the JSON."
)


class LLMAnalysisError(Exception):
    pass


class GroqAnalysisService:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL

    def analyze(self, product, score: ScoreBreakdown, metrics=None) -> AnalysisResult:
        prompt = self._build_prompt(product, score, metrics)

        raw = self._call_llm(prompt)
        try:
            return AnalysisResult.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError):
            # One retry with a stricter nudge - LLMs occasionally wrap JSON in prose.
            raw = self._call_llm(prompt + "\n\nRespond with raw JSON only, nothing else.")
            try:
                return AnalysisResult.model_validate(json.loads(raw))
            except (json.JSONDecodeError, ValidationError) as exc:
                raise LLMAnalysisError(f"Could not parse LLM response as valid analysis: {raw}") from exc

    def _call_llm(self, prompt: str) -> str:
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        return completion.choices[0].message.content

    def _build_prompt(self, product, score: ScoreBreakdown, metrics=None) -> str:
        # Raw numbers alongside the scores, so the LLM can sanity-check the score instead of
        # only echoing it.
        lines = {
            "Units sold (lifetime)": "hpm_units_sold",
            f"Estimated lifetime revenue ({product['mp_currency']})": "hpm_revenue",
            "Rating (out of 5)": "hpm_rating",
            "Total search results for the keyword (competition proxy)": "hpm_competitor_count",
        }
        # Missing values are left out rather than printed as "None", which reads like zero.
        raw = "".join(
            f"{label}: {metrics[key]}\n"
            for label, key in lines.items()
            if metrics and metrics.get(key) is not None
        )
        return (
            f"Product: {product['mp_name']}\n"
            f"Category: {product['mp_category']}\n"
            f"Price: {product['mp_price']} {product['mp_currency']}\n"
            f"Shop: {product['mp_shop_name']}\n"
            f"{raw}"
            f"Score breakdown: total={score.total_score}, "
            f"sales_velocity={score.sales_velocity_score}, "
            f"growth={score.growth_score}, rating={score.rating_score}, "
            f"competition={score.competition_score}"
        )
