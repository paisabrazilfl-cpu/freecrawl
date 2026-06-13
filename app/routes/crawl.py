"""
POST /crawl  — enqueue a recursive crawl job (returns jobId immediately).
GET  /crawl/:jobId — poll status + paginated results.
"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.models import CrawlRequest, CrawlJobStatus
from app.database import get_db, CrawlJob, CrawlPage
from app.config import settings
import redis
from rq import Queue

router = APIRouter()

_redis = redis.from_url(settings.redis_url)
_queue = Queue("crawl", connection=_redis)


@router.post("/crawl", response_model=CrawlJobStatus, status_code=202)
def start_crawl(req: CrawlRequest, db: Session = Depends(get_db)) -> CrawlJobStatus:
    job_id = str(uuid.uuid4())
    job = CrawlJob(
        id=job_id,
        url=req.url,
        status="queued",
        max_pages=min(req.max_pages, settings.max_crawl_pages),
        max_depth=min(req.max_depth, settings.max_crawl_depth),
        include_patterns=req.include_patterns,
        exclude_patterns=req.exclude_patterns,
    )
    db.add(job)
    db.commit()

    _queue.enqueue(
        "worker.run_crawl",
        job_id,
        req.url,
        req.max_pages,
        req.max_depth,
        req.include_patterns,
        req.exclude_patterns,
        job_timeout=600,
    )

    return CrawlJobStatus(
        job_id=job_id,
        status="queued",
        url=req.url,
        pages_found=0,
        pages_done=0,
        error=None,
        created_at=job.created_at,
        finished_at=None,
    )


@router.get("/crawl/{job_id}", response_model=CrawlJobStatus)
def get_crawl(job_id: str, include_pages: bool = False, db: Session = Depends(get_db)) -> CrawlJobStatus:
    job = db.query(CrawlJob).filter(CrawlJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    pages = None
    if include_pages:
        rows = db.query(CrawlPage).filter(CrawlPage.job_id == job_id).all()
        pages = [
            {
                "url": r.url,
                "title": r.title,
                "markdown": r.markdown,
                "status_code": r.status_code,
                "error": r.error,
            }
            for r in rows
        ]

    return CrawlJobStatus(
        job_id=job.id,
        status=job.status,
        url=job.url,
        pages_found=job.pages_found,
        pages_done=job.pages_done,
        error=job.error,
        created_at=job.created_at,
        finished_at=job.finished_at,
        pages=pages,
    )
