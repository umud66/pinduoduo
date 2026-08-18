from __future__ import annotations

import shutil
import subprocess
import threading
import webbrowser
from pathlib import Path

import uvicorn

from app.core.config import get_settings


ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"


def _start_frontend() -> subprocess.Popen[str]:
    npm = shutil.which("npm")
    if npm is None:
        raise RuntimeError("Vue 开发环境需要 Node.js/npm；正式 Release 用户不需要安装 Node.js。")
    if not (FRONTEND / "node_modules").exists():
        subprocess.run([npm, "install"], cwd=FRONTEND, check=True)
    return subprocess.Popen([npm, "run", "dev"], cwd=FRONTEND, text=True)


if __name__ == "__main__":
    settings = get_settings()
    frontend = _start_frontend()
    try:
        if settings.auto_open_browser:
            threading.Timer(1.2, webbrowser.open, args=("http://127.0.0.1:5173",)).start()
        uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
    finally:
        frontend.terminate()
