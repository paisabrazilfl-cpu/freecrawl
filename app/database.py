from sqlalchemy import create_engine, Column, String, Text, Integer, DateTime, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone
from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    id = Column(String(36), primary_key=True)
    url = Column(Text, nullable=False)
    status = Column(String(20), default="queued")  # queued | running | done | failed
    max_pages = Column(Integer, default=50)
    max_depth = Column(Integer, default=3)
    include_patterns = Column(JSON, default=list)
    exclude_patterns = Column(JSON, default=list)
    pages_found = Column(Integer, default=0)
    pages_done = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime, nullable=True)


class CrawlPage(Base):
    __tablename__ = "crawl_pages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(36), nullable=False, index=True)
    url = Column(Text, nullable=False)
    title = Column(Text, nullable=True)
    markdown = Column(Text, nullable=True)
    html = Column(Text, nullable=True)
    status_code = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)
    crawled_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
