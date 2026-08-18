from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.ai import router as ai_router
from app.api.data import router as data_router
from app.api.diagnosis import router as diagnosis_router
from app.api.health import router as health_router
from app.api.optimization import router as optimization_router
from app.api.pdd import router as pdd_router
from app.api.pdd_auth import router as pdd_auth_router
from app.api.sync import router as sync_router
from app.api.workspace import router as workspace_router
from app.core.config import get_settings
from app.db.database import init_database
from app.services.pdd.auth_refresh import pdd_token_refresh_scheduler
from app.services.pdd.runner import auto_sync_scheduler, sync_runner

@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_database()
    sync_runner.recover_stale_jobs()
    auto_sync_scheduler.start()
    pdd_token_refresh_scheduler.start()
    yield
    pdd_token_refresh_scheduler.stop()
    auto_sync_scheduler.stop()
    sync_runner.shutdown()

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.6.0", lifespan=lifespan)
app.include_router(health_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(data_router, prefix="/api")
app.include_router(diagnosis_router, prefix="/api")
app.include_router(optimization_router, prefix="/api")
app.include_router(pdd_router, prefix="/api")
app.include_router(pdd_auth_router, prefix="/api")
app.include_router(sync_router, prefix="/api")
app.include_router(workspace_router, prefix="/api")

static_dir = Path(__file__).resolve().parent / "static"
assets_dir = static_dir / "assets"
app.mount("/assets", StaticFiles(directory=assets_dir, check_dir=False), name="frontend-assets")

def _frontend_index():
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("""<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<title>前端尚未构建</title><body style="font-family:sans-serif;padding:40px">
<h2>Vue 前端尚未构建</h2><p>开发环境请在 frontend 目录运行 npm install && npm run dev。</p>
<p>正式多平台 Release 会在 GitHub Actions 中自动构建前端。</p></body></html>""", status_code=503)

@app.get("/", include_in_schema=False)
def index():
    return _frontend_index()

@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str):
    return _frontend_index()
