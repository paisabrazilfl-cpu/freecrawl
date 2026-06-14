from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://freecrawl:freecrawl@postgres:5432/freecrawl"
    redis_url: str = "redis://redis:6379/0"
    max_concurrency: int = 5
    request_timeout: int = 30
    max_crawl_pages: int = 500
    max_crawl_depth: int = 5

    # Scheduled maintenance (app.cron) — see render.yaml `freecrawl-cron`.
    self_url: str = ""                  # base API URL to keep-alive ping; "" disables
    cron_interval_seconds: int = 600    # 10 minutes (used by --loop mode)
    cron_requeue_after_minutes: int = 15  # re-enqueue jobs stuck in "queued"
    cron_stale_after_minutes: int = 30    # fail jobs stuck in "running"

    class Config:
        env_file = ".env"


settings = Settings()
