from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.router_drafts import router as drafts_router
from .api.router_publish import router as publish_router
from .api.router_seeds import router as seeds_router
from .api.router_sources import router as sources_router

app = FastAPI(title="social-agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4321"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sources_router, prefix="/api")
app.include_router(seeds_router, prefix="/api")
app.include_router(drafts_router, prefix="/api")
app.include_router(publish_router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
