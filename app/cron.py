"""
FreeCrawl scheduled maintenance task.

Runs every 10 minutes (see render.yaml `freecrawl-cron` service and the
`cron` service in docker-compose.yml). Each tick performs lightweight
housekeeping so the deployment stays healthy without manual intervention:

  1. Heartbeat  — log a UTC timestamp so liveness is visible in logs.
  2. Keep-alive — optionally ping the web service (FREECRAWL_SELF_URL) to
                  stop free/idle hosting tiers from spinning the API down.
  3. Reap jobs  — re-enqueue jobs that were left "queued" (e.g. the worker
                  was down when they came in) and fail "running" jobs that
                  have clearly stalled past their timeout.

Run modes:
    python -m app.cron            # single tick (for a native cron scheduler)
    python -m app.cron --loop     # run forever, sleeping CRON_INTERVAL_SECONDS
"""
import sys
import time
from datetime import datetime, timezone, timedelta

import httpx
import redis
from rq import Queue

from app.config import settings
from app.database import SessionLocal, CrawlJob


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _log(msg: str) -> None:
    print(f"[cron {_now().isoformat()}] {msg}", flush=True)


def keep_alive() -> None:
    """Ping the API so idle hosting tiers don't spin the web service down."""
    url = settings.self_url
    if not url:
        return
    if "://" not in url:  # Render's fromService `host` property has no scheme
        url = "https://" + url
    health = url.rstrip("/") + "/health"
    try:
        resp = httpx.get(health, timeout=10)
        _log(f"keep-alive {health} -> {resp.status_code}")
    except Exception as exc:  # network hiccups shouldn't crash the tick
        _log(f"keep-alive failed for {health}: {exc}")


def reap_jobs() -> None:
    """Recover stuck jobs so a transient worker outage self-heals."""
    db = SessionLocal()
    try:
        queue = Queue("crawl", connection=redis.from_url(settings.redis_url))
        now = _now()
        requeue_before = now - timedelta(minutes=settings.cron_requeue_after_minutes)
        fail_before = now - timedelta(minutes=settings.cron_stale_after_minutes)

        # Re-enqueue jobs that were never picked up by a worker.
        stuck = (
            db.query(CrawlJob)
            .filter(CrawlJob.status == "queued", CrawlJob.created_at < requeue_before)
            .all()
        )
        for job in stuck:
            queue.enqueue(
                "worker.run_crawl",
                job.id,
                job.url,
                job.max_pages,
                job.max_depth,
                job.include_patterns or [],
                job.exclude_patterns or [],
                job_timeout=600,
            )
            _log(f"re-enqueued stalled job {job.id} ({job.url})")

        # Fail jobs that have been "running" well past their timeout.
        stale = (
            db.query(CrawlJob)
            .filter(CrawlJob.status == "running", CrawlJob.created_at < fail_before)
            .all()
        )
        for job in stale:
            job.status = "failed"
            job.error = "Job timed out (reaped by cron)"
            job.finished_at = now
            _log(f"failed stale running job {job.id} ({job.url})")

        if stuck or stale:
            db.commit()
    except Exception as exc:
        _log(f"reap_jobs error: {exc}")
    finally:
        db.close()


def tick() -> None:
    _log("heartbeat — waking up")
    keep_alive()
    reap_jobs()
    _log("heartbeat — done")


def main() -> None:
    if "--loop" in sys.argv:
        interval = settings.cron_interval_seconds
        _log(f"starting loop mode, every {interval}s")
        while True:
            try:
                tick()
            except Exception as exc:
                _log(f"tick error: {exc}")
            time.sleep(interval)
    else:
        tick()


if __name__ == "__main__":
    main()
