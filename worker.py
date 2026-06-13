"""
RQ worker entry point.
Run with: rq worker crawl --with-scheduler
"""
import asyncio
import re
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin
import httpx
from app.database import SessionLocal, CrawlJob, CrawlPage
from app.extractor import extract_from_html, extract_links
from app.config import settings


def _same_domain(url: str, domain: str) -> bool:
    return urlparse(url).netloc == domain


def _matches(url: str, patterns: list[str]) -> bool:
    return any(re.search(p, url) for p in patterns)


def run_crawl(
    job_id: str,
    start_url: str,
    max_pages: int,
    max_depth: int,
    include_patterns: list[str],
    exclude_patterns: list[str],
) -> None:
    asyncio.run(
        _async_crawl(job_id, start_url, max_pages, max_depth, include_patterns, exclude_patterns)
    )


async def _async_crawl(
    job_id: str,
    start_url: str,
    max_pages: int,
    max_depth: int,
    include_patterns: list[str],
    exclude_patterns: list[str],
) -> None:
    db = SessionLocal()
    try:
        job = db.query(CrawlJob).filter(CrawlJob.id == job_id).first()
        if not job:
            return

        job.status = "running"
        db.commit()

        domain = urlparse(start_url).netloc
        visited: set[str] = set()
        # queue items: (url, depth)
        queue: list[tuple[str, int]] = [(start_url, 0)]
        pages_done = 0

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; FreeCrawl/1.0)",
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        }

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=settings.request_timeout,
            headers=headers,
            limits=httpx.Limits(max_connections=settings.max_concurrency),
        ) as client:
            while queue and pages_done < max_pages:
                url, depth = queue.pop(0)
                if url in visited:
                    continue
                visited.add(url)

                # Pattern filters
                if include_patterns and not _matches(url, include_patterns):
                    continue
                if exclude_patterns and _matches(url, exclude_patterns):
                    continue

                try:
                    resp = await client.get(url)
                    status_code = resp.status_code
                    html = resp.text if status_code < 400 else ""
                except Exception as exc:
                    page = CrawlPage(
                        job_id=job_id, url=url, error=str(exc), status_code=None
                    )
                    db.add(page)
                    db.commit()
                    continue

                extracted = extract_from_html(html, url, want_markdown=True)

                page = CrawlPage(
                    job_id=job_id,
                    url=url,
                    title=extracted.get("title"),
                    markdown=extracted.get("markdown"),
                    status_code=status_code,
                    error=extracted.get("error"),
                )
                db.add(page)
                pages_done += 1
                job.pages_done = pages_done
                job.pages_found = len(visited)
                db.commit()

                if depth < max_depth and html:
                    links = extract_links(html, url)
                    for link in links:
                        if (
                            _same_domain(link, domain)
                            and link not in visited
                        ):
                            queue.append((link, depth + 1))

        job.status = "done"
        job.finished_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as exc:
        try:
            job.status = "failed"
            job.error = str(exc)
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
        except Exception:
            pass
    finally:
        db.close()
