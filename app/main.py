from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.ai import router as ai_router
from app.api.data import router as data_router
from app.api.diagnosis import router as diagnosis_router
from app.api.health import router as health_router
from app.api.pdd import router as pdd_router
from app.api.workspace import router as workspace_router
from app.core.config import get_settings
from app.db.database import init_database


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_database()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.include_router(health_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(data_router, prefix="/api")
app.include_router(diagnosis_router, prefix="/api")
app.include_router(pdd_router, prefix="/api")
app.include_router(workspace_router, prefix="/api")

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")
