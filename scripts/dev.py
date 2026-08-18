from __future__ import annotations

import threading
import webbrowser

import uvicorn

from app.core.config import get_settings


if __name__ == "__main__":
    settings = get_settings()
    if settings.auto_open_browser:
        threading.Timer(1.0, webbrowser.open, args=(f"http://{settings.host}:{settings.port}",)).start()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
