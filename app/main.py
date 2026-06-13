from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import init_db
from app.routes import scrape, crawl, map, extract


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="FreeCrawl",
    description="Open-source Firecrawl-compatible web crawler API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scrape.router)
app.include_router(crawl.router)
app.include_router(map.router)
app.include_router(extract.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "freecrawl"}
