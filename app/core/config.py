import math

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "TikTok Product Research"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database (Postgres - e.g. Neon)
    PGHOST: str
    PGDATABASE: str
    PGUSER: str
    PGPASSWORD: str
    PGSSLMODE: str = "require"
    PGCHANNELBINDING: str = "require"
    # Seconds per address - without it libpq waits forever when a network silently drops port 5432.
    PGCONNECT_TIMEOUT: int = 10

    # LLM (Groq) - must support "json_mode" (see models.json)
    GROQ_API_KEY: str
    GROQ_MODEL: str = "openai/gpt-oss-120b"

    # Scoring weights
    SCORE_WEIGHT_SALES_VELOCITY: float = 0.4
    SCORE_WEIGHT_GROWTH: float = 0.25
    SCORE_WEIGHT_RATING: float = 0.15
    SCORE_WEIGHT_COMPETITION: float = 0.2

    @model_validator(mode="after")
    def _weights_sum_to_one(self):
        total = (
            self.SCORE_WEIGHT_SALES_VELOCITY
            + self.SCORE_WEIGHT_GROWTH
            + self.SCORE_WEIGHT_RATING
            + self.SCORE_WEIGHT_COMPETITION
        )
        if not math.isclose(total, 1.0, abs_tol=1e-6):
            raise ValueError(f"SCORE_WEIGHT_* must sum to 1.0, got {total}")
        return self

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.PGUSER}:{self.PGPASSWORD}"
            f"@{self.PGHOST}/{self.PGDATABASE}"
            f"?sslmode={self.PGSSLMODE}&channel_binding={self.PGCHANNELBINDING}"
            f"&connect_timeout={self.PGCONNECT_TIMEOUT}"
        )


settings = Settings()
