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
    # App-wide default (every route not explicitly decorated with its own
    # tighter @limiter.limit(...)) — see app/rate_limit.py.
    default_rate_limit: str = "60/minute"

    # --- Uploads ------------------------------------------------------------
    # Local disk by default (zero setup for dev/tests). Set all four r2_*
    # values to switch to Cloudflare R2 — required in production, since
    # Render's free-tier filesystem is ephemeral and wipes /tmp on restart.
    upload_dir: str = "./uploads"
    max_upload_mb: int = 25  # per-file limit
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""

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

    # --- External integrations (1С и т.п.) ----------------------------------
    # Токен для входящего вебхука статуса оплаты из 1С
    # (POST /api/internal/1c/payment-status). Пусто = эндпоинт выключен (403).
    onec_service_token: str = ""
    # Email (если заданы host+from — канал email включён):
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_tls: bool = True
    # Telegram (если задан токен — канал telegram включён, нужен chat_id у юзера):
    telegram_bot_token: str = ""

    # --- Error monitoring (Sentry) -------------------------------------------
    # Пусто = мониторинг выключен. Создать проект на sentry.io и задать
    # SENTRY_DSN в Render dashboard (или .env локально), чтобы включить.
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.0  # perf-трейсинг выкл. по умолчанию

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
    def r2_enabled(self) -> bool:
        return bool(
            self.r2_account_id
            and self.r2_access_key_id
            and self.r2_secret_access_key
            and self.r2_bucket_name
        )

    @property
    def sentry_enabled(self) -> bool:
        return bool(self.sentry_dsn)

    @property
    def sqlalchemy_database_url(self) -> str:
        # Managed Postgres providers (Render, Heroku, Railway, Supabase, ...)
        # hand out `postgres://` / plain `postgresql://` URLs; SQLAlchemy needs
        # the psycopg3 dialect spelled out explicitly.
        url = self.database_url
        if url.startswith("postgres://"):
            return "postgresql+psycopg://" + url[len("postgres://") :]
        if url.startswith("postgresql://"):
            return "postgresql+psycopg://" + url[len("postgresql://") :]
        return url

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
