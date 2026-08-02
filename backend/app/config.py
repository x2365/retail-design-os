"""Application configuration.

All settings are read from environment variables so the same image can run
unchanged in dev, staging and production. In production point DATABASE_URL at
PostgreSQL; locally it falls back to SQLite so the app runs with zero setup.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Core ---------------------------------------------------------------
    app_name: str = "RetailDesign OS API"
    environment: str = "development"  # development | staging | production
    api_prefix: str = "/api"

    # --- Database -----------------------------------------------------------
    # Example prod value:
    #   postgresql+psycopg://user:pass@db-host:5432/retaildesign
    database_url: str = "sqlite:///./retaildesign.db"

    # Connection pool (ignored by SQLite, used by Postgres)
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800

    # --- CORS ---------------------------------------------------------------
    # Comma-separated list of allowed origins for the browser frontend.
    cors_origins: str = "*"

    # --- Auth ---------------------------------------------------------------
    # In production set a strong JWT_SECRET via environment.
    jwt_secret: str = "CHANGE-ME-in-production-please-use-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12  # 12h

    # Brute-force mitigation on /auth/login (slowapi / limits syntax, e.g. "5/minute").
    login_rate_limit: str = "5/minute"

    # --- Uploads ------------------------------------------------------------
    upload_dir: str = "./uploads"  # mount a volume here in production
    max_upload_mb: int = 25  # per-file limit

    # --- Pagination ---------------------------------------------------------
    default_page_size: int = 50
    max_page_size: int = 200

    # --- Seed ---------------------------------------------------------------
    seed_on_startup: bool = True

    # --- LLM copilot (локальный ассистент-копайлот) ------------------------
    # По умолчанию выключен. Включается, когда локально запущена Ollama с
    # моделью Qwen2.5. Данные никуда не уходят — модель работает на машине.
    llm_enabled: bool = False
    llm_base_url: str = "http://localhost:11434/v1"  # OpenAI-совместимый API Ollama
    llm_model: str = "qwen2.5:7b-instruct"
    llm_api_key: str = "ollama"  # Ollama игнорирует, но клиент требует непустое
    llm_timeout: int = 60
    llm_max_tool_rounds: int = 5

    # --- Reminders / notifications -----------------------------------------
    # Токен для защищённого запуска обхода напоминаний (cron → эндпоинт).
    reminders_service_token: str = ""
    # Email (если заданы host+from — канал email включён):
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_tls: bool = True
    # Telegram (если задан токен — канал telegram включён, нужен chat_id у юзера):
    telegram_bot_token: str = ""

    @property
    def email_enabled(self) -> bool:
        return bool(self.smtp_host and self.smtp_from)

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_bot_token)

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def docs_enabled(self) -> bool:
        # Hide Swagger/OpenAPI in production to reduce attack surface.
        return not self.is_production

    def validate_runtime(self) -> None:
        """Fail fast on insecure production configuration."""
        if self.is_production and self.jwt_secret.startswith("CHANGE-ME"):
            raise RuntimeError(
                "JWT_SECRET must be set to a strong random value in production "
                "(the default placeholder is not allowed)."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
