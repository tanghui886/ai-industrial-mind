"""ContainerMind API 入口"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import SessionLocal, init_db
from .routers import ALL_ROUTERS
from .seed import seed

app = FastAPI(title=settings.APP_NAME, description=settings.APP_DESC, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in ALL_ROUTERS:
    app.include_router(r, prefix=settings.API_PREFIX)


@app.on_event("startup")
def on_startup():
    Path(settings.DATABASE_URL.split("///")[-1]).parent.mkdir(parents=True, exist_ok=True) \
        if settings.DATABASE_URL.startswith("sqlite") else None
    init_db()
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()


@app.get("/")
def root():
    return {"app": settings.APP_NAME, "docs": "/docs", "api_prefix": settings.API_PREFIX}


@app.get(f"{settings.API_PREFIX}/health")
def health():
    return {"status": "ok"}
