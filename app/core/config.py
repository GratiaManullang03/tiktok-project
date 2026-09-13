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

    # LLM (Groq) - must support "json_mode" (see models.json)
    GROQ_API_KEY: str
    GROQ_MODEL: str = "openai/gpt-oss-120b"

    # Scoring weights
    SCORE_WEIGHT_SALES_VELOCITY: float = 0.4
    SCORE_WEIGHT_GROWTH: float = 0.25
    SCORE_WEIGHT_RATING: float = 0.15
    SCORE_WEIGHT_COMPETITION: float = 0.2

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.PGUSER}:{self.PGPASSWORD}"
            f"@{self.PGHOST}/{self.PGDATABASE}"
            f"?sslmode={self.PGSSLMODE}&channel_binding={self.PGCHANNELBINDING}"
        )


settings = Settings()
