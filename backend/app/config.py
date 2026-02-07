from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Gemini AI
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_rpm_delay: float = 6.0  # seconds between requests (free tier: 10 RPM)
    gemini_max_batch: int = 30  # max articles per scheduler run

    # Naver Search API
    naver_client_id: str = ""
    naver_client_secret: str = ""

    # Finnhub API
    finnhub_api_key: str = ""

    # Database
    database_url: str = "sqlite+aiosqlite:///./market_news.db"

    # CORS
    cors_origins: str = "http://localhost:5173"

    # Environment
    env: str = "development"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
