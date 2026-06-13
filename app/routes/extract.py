"""
POST /extract — scrape a URL, extract structured JSON matching a provided schema.
Uses the page markdown + a local heuristic (field-name matching) for MVP.
No LLM dependency — pure extraction from structured content.
"""
import re
import json
from fastapi import APIRouter
from app.models import ExtractRequest
from app.extractor import fetch_and_extract
from app.browser import fetch_with_browser
from app.extractor import extract_from_html

router = APIRouter()


def _heuristic_extract(markdown: str, schema: dict) -> dict:
    """
    Walk each key in the schema and try to find a matching value in the markdown.
    Schema format: { "fieldName": "string|number|list", ... }
    """
    result: dict = {}
    lines = markdown.split("\n") if markdown else []
    for field, typ in schema.items():
        pattern = re.compile(
            rf"(?i){re.escape(field)}[\s:*_-]{{0,5}}(.{{1,300}})", re.MULTILINE
        )
        m = pattern.search(markdown or "")
        if m:
            raw = m.group(1).strip().strip("*_:").strip()
            if typ == "number":
                nums = re.findall(r"[\d,.]+", raw)
                result[field] = nums[0] if nums else None
            elif typ == "list":
                result[field] = [raw]
            else:
                result[field] = raw
        else:
            result[field] = None
    return result


@router.post("/extract")
async def extract(req: ExtractRequest) -> dict:
    if req.use_browser:
        try:
            html, status_code = await fetch_with_browser(req.url)
        except Exception as exc:
            return {"url": req.url, "error": str(exc), "json": None}
        extracted = extract_from_html(html, req.url, want_markdown=True)
        extracted["status_code"] = status_code
    else:
        extracted = await fetch_and_extract(req.url, want_markdown=True)

    if extracted.get("error"):
        return {"url": req.url, "error": extracted["error"], "json": None}

    data = _heuristic_extract(extracted.get("markdown") or "", req.fields)
    return {
        "url": req.url,
        "json": data,
        "source_markdown": extracted.get("markdown"),
        "title": extracted.get("title"),
        "status_code": extracted.get("status_code"),
        "error": None,
    }
