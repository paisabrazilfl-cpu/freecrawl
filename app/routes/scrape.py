from fastapi import APIRouter
from app.models import ScrapeRequest, ScrapeResult
from app.extractor import fetch_and_extract
from app.browser import fetch_with_browser
from app.extractor import extract_from_html

router = APIRouter()


@router.post("/scrape", response_model=ScrapeResult)
async def scrape(req: ScrapeRequest) -> ScrapeResult:
    want_markdown = "markdown" in req.formats
    want_html = "html" in req.formats
    want_text = "text" in req.formats
    want_links = "links" in req.formats or req.include_links

    if req.use_browser:
        try:
            html, status_code = await fetch_with_browser(req.url, wait_ms=req.wait_for)
        except Exception as exc:
            return ScrapeResult(url=req.url, title=None, markdown=None, html=None,
                                text=None, links=None, metadata=None,
                                status_code=None, error=str(exc))

        extracted = extract_from_html(
            html, req.url,
            want_markdown=want_markdown,
            want_html=want_html,
            want_text=want_text,
            want_links=want_links,
        )
        extracted["status_code"] = status_code
    else:
        extracted = await fetch_and_extract(
            req.url,
            want_markdown=want_markdown,
            want_html=want_html,
            want_text=want_text,
            want_links=want_links,
        )

    return ScrapeResult(
        url=extracted.get("url", req.url),
        title=extracted.get("title"),
        markdown=extracted.get("markdown") if want_markdown else None,
        html=extracted.get("html") if want_html else None,
        text=extracted.get("text") if want_text else None,
        links=extracted.get("links") if want_links else None,
        metadata=extracted.get("metadata"),
        status_code=extracted.get("status_code"),
        error=extracted.get("error"),
    )
