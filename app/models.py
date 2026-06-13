from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Any
from datetime import datetime


class ScrapeRequest(BaseModel):
    url: str
    formats: List[str] = ["markdown"]  # markdown | html | text | links
    wait_for: Optional[int] = None     # ms to wait after page load
    include_links: bool = False
    use_browser: bool = False          # False = httpx (fast), True = Playwright


class ScrapeResult(BaseModel):
    url: str
    title: Optional[str]
    markdown: Optional[str]
    html: Optional[str]
    text: Optional[str]
    links: Optional[List[str]]
    metadata: Optional[dict]
    status_code: Optional[int]
    error: Optional[str]


class CrawlRequest(BaseModel):
    url: str
    max_pages: int = Field(default=50, le=500)
    max_depth: int = Field(default=3, le=5)
    include_patterns: List[str] = []
    exclude_patterns: List[str] = []


class CrawlJobStatus(BaseModel):
    job_id: str
    status: str
    url: str
    pages_found: int
    pages_done: int
    error: Optional[str]
    created_at: datetime
    finished_at: Optional[datetime]
    pages: Optional[List[dict]] = None


class MapRequest(BaseModel):
    url: str
    max_urls: int = Field(default=200, le=1000)


class MapResult(BaseModel):
    url: str
    urls: List[str]
    count: int


class ExtractRequest(BaseModel):
    url: str
    fields: dict  # { "fieldName": "string|number|list", ... }
    prompt: Optional[str] = None
    use_browser: bool = False
