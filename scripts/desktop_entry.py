from __future__ import annotations

import threading
import webbrowser

import uvicorn

from app.core.config import get_settings
from app.main import app


def open_browser(url: str) -> None:
    threading.Timer(1.2, webbrowser.open, args=(url,)).start()


if __name__ == "__main__":
    settings = get_settings()
    url = f"http://{settings.host}:{settings.port}"
    if settings.auto_open_browser:
        open_browser(url)
    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")
