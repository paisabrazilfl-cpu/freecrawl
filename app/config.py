from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://freecrawl:freecrawl@postgres:5432/freecrawl"
    redis_url: str = "redis://redis:6379/0"
    max_concurrency: int = 5
    request_timeout: int = 30
    max_crawl_pages: int = 500
    max_crawl_depth: int = 5

    class Config:
        env_file = ".env"


settings = Settings()
