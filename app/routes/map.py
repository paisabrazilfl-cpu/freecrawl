"""
POST /map — discover all URLs on a domain via sitemap.xml + recursive link discovery.
"""
from fastapi import APIRouter
from app.models import MapRequest, MapResult
from app.extractor import fetch_and_extract
from urllib.parse import urlparse, urljoin
import httpx
import xml.etree.ElementTree as ET

router = APIRouter()

_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


async def _fetch_sitemap_urls(base: str) -> list[str]:
    urls: list[str] = []
    candidates = [
        urljoin(base, "/sitemap.xml"),
        urljoin(base, "/sitemap_index.xml"),
        urljoin(base, "/sitemap/sitemap.xml"),
    ]
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        for url in candidates:
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    continue
                root = ET.fromstring(resp.text)
                # Sitemap index — recurse
                for loc in root.findall(".//sm:loc", _NS):
                    text = (loc.text or "").strip()
                    if text.endswith(".xml"):
                        try:
                            sub = await client.get(text)
                            sub_root = ET.fromstring(sub.text)
                            for sloc in sub_root.findall(".//sm:loc", _NS):
                                if sloc.text:
                                    urls.append(sloc.text.strip())
                        except Exception:
                            pass
                    elif text:
                        urls.append(text)
                if urls:
                    break
            except Exception:
                continue
    return urls


async def _crawl_links(start: str, max_urls: int, base_domain: str) -> list[str]:
    visited: set[str] = set()
    queue: list[str] = [start]
    found: list[str] = []

    async with httpx.AsyncClient(follow_redirects=True, timeout=15,
                                  headers={"User-Agent": "FreeCrawl/1.0"}) as client:
        while queue and len(found) < max_urls:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)

            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    continue
                html = resp.text
            except Exception:
                continue

            found.append(url)

            from app.extractor import extract_links
            links = extract_links(html, url)
            for link in links:
                p = urlparse(link)
                if p.netloc == base_domain and link not in visited:
                    queue.append(link)

    return found


@router.post("/map", response_model=MapResult)
async def map_site(req: MapRequest) -> MapResult:
    parsed = urlparse(req.url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    domain = parsed.netloc

    # Try sitemap first (fast path)
    urls = await _fetch_sitemap_urls(base)

    # Fall back to crawl-based discovery if sitemap empty
    if not urls:
        urls = await _crawl_links(req.url, req.max_urls, domain)

    # Deduplicate, cap, same-domain filter
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if urlparse(u).netloc == domain and u not in seen:
            seen.add(u)
            out.append(u)
        if len(out) >= req.max_urls:
            break

    return MapResult(url=req.url, urls=out, count=len(out))
