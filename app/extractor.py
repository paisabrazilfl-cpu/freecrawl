"""
Content extraction layer: raw HTML → clean Markdown / text / metadata.
Uses Trafilatura as primary extractor with httpx fallback for HTTP fetch.
"""
import trafilatura
from trafilatura.settings import use_config
import httpx
from typing import Optional
from urllib.parse import urljoin, urlparse
from html.parser import HTMLParser


_traf_config = use_config()
_traf_config.set("DEFAULT", "EXTRACTION_TIMEOUT", "30")


class _LinkExtractor(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base = base_url
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        if tag == "a":
            for k, v in attrs:
                if k == "href" and v:
                    full = urljoin(self.base, v.strip())
                    parsed = urlparse(full)
                    if parsed.scheme in ("http", "https"):
                        self.links.append(full)


def extract_links(html: str, base_url: str) -> list[str]:
    p = _LinkExtractor(base_url)
    p.feed(html)
    seen: set[str] = set()
    out: list[str] = []
    for link in p.links:
        if link not in seen:
            seen.add(link)
            out.append(link)
    return out


def extract_from_html(
    html: str,
    url: str,
    want_markdown: bool = True,
    want_html: bool = False,
    want_text: bool = False,
    want_links: bool = False,
) -> dict:
    result: dict = {"url": url, "error": None}

    meta = trafilatura.extract_metadata(filecontent=html, default_url=url)
    result["title"] = meta.title if meta else None
    result["metadata"] = {
        "author": meta.author if meta else None,
        "date": meta.date if meta else None,
        "description": meta.description if meta else None,
        "sitename": meta.sitename if meta else None,
        "tags": meta.tags if meta else None,
    }

    if want_markdown:
        result["markdown"] = trafilatura.extract(
            html,
            url=url,
            output_format="markdown",
            config=_traf_config,
            include_links=True,
            include_images=True,
        )

    if want_html:
        result["html"] = trafilatura.extract(
            html,
            url=url,
            output_format="xml",
            config=_traf_config,
        )

    if want_text:
        result["text"] = trafilatura.extract(
            html,
            url=url,
            output_format="txt",
            config=_traf_config,
        )

    if want_links:
        result["links"] = extract_links(html, url)

    return result


async def fetch_and_extract(
    url: str,
    want_markdown: bool = True,
    want_html: bool = False,
    want_text: bool = False,
    want_links: bool = False,
    timeout: int = 30,
) -> dict:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; FreeCrawl/1.0; +https://github.com/freecrawl)"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers=headers,
        ) as client:
            resp = await client.get(url)
            status_code = resp.status_code
            html = resp.text
    except Exception as exc:
        return {"url": url, "error": str(exc), "status_code": None}

    extracted = extract_from_html(
        html, url,
        want_markdown=want_markdown,
        want_html=want_html,
        want_text=want_text,
        want_links=want_links,
    )
    extracted["status_code"] = status_code
    return extracted
