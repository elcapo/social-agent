from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.router_drafts import router as drafts_router
from .api.router_ideas import router as ideas_router
from .api.router_publish import router as publish_router
from .api.router_seeds import router as seeds_router
from .api.router_sources import router as sources_router
from .config import settings

app = FastAPI(title="social-agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4321"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sources_router, prefix="/api")
app.include_router(seeds_router, prefix="/api")
app.include_router(ideas_router, prefix="/api")
app.include_router(drafts_router, prefix="/api")
app.include_router(publish_router, prefix="/api")

media_dir = settings.data_dir.resolve() / "media"
media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/api/media", StaticFiles(directory=str(media_dir)), name="media")


@app.get("/api/health")
def health():
    return {"status": "ok"}
