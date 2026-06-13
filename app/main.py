from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import init_db
from app.routes import scrape, crawl, map, extract


@asynccontextmanager
async def lifespan(app: FastAPI):
    import time
    for attempt in range(10):
        try:
            init_db()
            break
        except Exception as exc:
            if attempt == 9:
                # Log but don't crash — health check still responds,
                # DB-backed routes will fail with 500 until DB is reachable.
                print(f"[startup] DB init failed after 10 attempts: {exc}")
            else:
                print(f"[startup] DB not ready (attempt {attempt+1}/10), retrying in 3s...")
                time.sleep(3)
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
