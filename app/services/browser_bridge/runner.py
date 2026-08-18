from __future__ import annotations

import importlib.util
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import desc, select

from app.core.config import get_settings
from app.db.browser_models import BrowserCaptureSession, BrowserNetworkRecord
from app.db.database import session_scope
from app.db.models import Shop
from app.services.browser_bridge.classifier import classify_response
from app.services.browser_bridge.sanitizer import (
    MAX_CAPTURE_BYTES,
    decode_and_sanitize,
    host_allowed,
    is_capture_content_type,
    safe_url,
)

DEFAULT_PDD_DOMAINS = ["pinduoduo.com", "yangkeduo.com"]


def playwright_available() -> bool:
    return importlib.util.find_spec("playwright") is not None


def validate_start_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("浏览器赛始地址必须是完整的 http/https URL")
    return value.strip()


def normalize_domains(values: list[str] | None) -> list[str]:
    domains: list[str] = []
    for raw in values or DEFAULT_PDD_DOMAINS:
        value = raw.lower().strip().lstrip(".").rstrip(".")
        if value and value not in domains:
            domains.append(value)
    if not domains:
        raise ValueError("至少需要一个允许采集的域名")
    if len(domains) > 20:
        raise ValueError("允许域名数量过多")
    return domains


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


class BrowserBridgeManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._active_session_id: int | None = None

    def status(self) -> dict[str, Any]:
        running = bool(self._thread and self._thread.is_alive())
        payload: dict[str, Any] = {
            "available": playwright_available(),
            "running": running,
            "active_session_id": self._active_session_id if running else None,
            "browser_engine": "chromium",
            "note": (
                "Browser Data Bridge 为实验功能；不会读取或保存 Cookie、Authorization 请求头、密码或验证码。"
            ),
        }
        if not playwright_available():
            payload["install_hint"] = 'pip install -e ".[browser]" && playwright install chromium'
        return payload

    def start(
        self,
        *,
        shop_id: int,
        start_url: str,
        allowed_domains: list[str] | None = None,
    ) -> int:
        if not playwright_available():
            raise RuntimeError("Playwright 未安装，请先安装 browser 可选依赖和 Chromium")
        url = validate_start_url(start_url)
        domains = normalize_domains(allowed_domains)
        with self._lock:
            if self._thread and self._thread.is_alive():
                raise RuntimeError("已有浏览器采集会话正在运行")
            with session_scope() as session:
                if session.get(Shop, shop_id) is None:
                    raise LookupError("店铺不存在")
                row = BrowserCaptureSession(
                    shop_id=shop_id,
                    status="starting",
                    start_url=url,
                    allowed_domains_json=_json(domains),
                )
                session.add(row)
                session.flush()
                session_id = row.id
            self._stop.clear()
            self._active_session_id = session_id
            self._thread = threading.Thread(
                target=self._run,
                kwargs={
                    "session_id": session_id,
                    "shop_id": shop_id,
                    "start_url": url,
                    "allowed_domains": domains,
                },
                daemon=True,
                name="browser-data-bridge",
            )
            self._thread.start()
            return session_id

    def stop(self) -> bool:
        with self._lock:
            if not self._thread or not self._thread.is_alive():
                return False
            self._stop.set()
            return True

    def shutdown(self, timeout: float = 3.0) -> None:
        self.stop()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=timeout)

    def _run(
        self,
        *,
        session_id: int,
        shop_id: int,
        start_url: str,
        allowed_domains: list[str],
    ) -> None:
        # Import inside the owning thread. Playwright's Python API is not thread-safe.
        from playwright.sync_api import sync_playwright

        settings = get_settings()
        root = settings.data_dir / "browser" / f"shop-{shop_id}"
        profile_dir = root / "profile"
        downloads_dir = root / "downloads"
        profile_dir.mkdir(parents=True, exist_ok=True)
        downloads_dir.mkdir(parents=True, exist_ok=True)

        with session_scope() as session:
            row = session.get(BrowserCaptureSession, session_id)
            if row:
                row.status = "running"
                row.started_at = datetime.utcnow()
                row.error_message = None

        try:
            with sync_playwright() as playwright:
                context = playwright.chromium.launch_persistent_context(
                    user_data_dir=str(profile_dir),
                    headless=False,
                    downloads_path=str(downloads_dir),
                    accept_downloads=True,
                )
                context.on(
                    "response",
                    lambda response: self._capture_response(
                        session_id=session_id,
                        shop_id=shop_id,
                        allowed_domains=allowed_domains,
                        response=response,
                    ),
                )
                pages = context.pages
                page = pages[0] if pages else context.new_page()
                page.goto(start_url, wait_until="domcontentloaded", timeout=60_000)
                while not self._stop.is_set():
                    try:
                        page.wait_for_timeout(250)
                    except Exception:
                        # The user may close the browser window themselves.
                        break
                try:
                    context.close()
                except Exception:
                    pass
            self._finish_session(session_id, "stopped", None)
        except Exception as exc:
            self._finish_session(session_id, "failed", str(exc))
        finally:
            with self._lock:
                if self._active_session_id == session_id:
                    self._active_session_id = None
                self._stop.clear()

    def _capture_response(
        self,
        *,
        session_id: int,
        shop_id: int,
        allowed_domains: list[str],
        response,
    ) -> None:
        try:
            if not host_allowed(response.url, allowed_domains):
                self._increment_skipped(session_id)
                return
            content_type = response.headers.get("content-type")
            if not is_capture_content_type(content_type):
                self._increment_skipped(session_id)
                return
            body = response.body()
            body_json, redacted_fields, capture_error = decode_and_sanitize(
                body, max_bytes=MAX_CAPTURE_BYTES
            )
            payload = json.loads(body_json) if body_json else {}
            category, evidence = classify_response(response.url, payload)
            cleaned_url, query_keys = safe_url(response.url)
            request = response.request
            with session_scope() as session:
                session.add(
                    BrowserNetworkRecord(
                        session_id=session_id,
                        shop_id=shop_id,
                        method=request.method,
                        url=cleaned_url,
                        query_keys_json=_json(query_keys),
                        status_code=response.status,
                        content_type=(content_type or "")[:256] or None,
                        resource_type=getattr(request, "resource_type", None),
                        category=category,
                        evidence_json=_json(evidence),
                        body_json=body_json,
                        body_bytes=len(body),
                        redacted_fields=redacted_fields,
                        capture_error=capture_error,
                    )
                )
                row = session.get(BrowserCaptureSession, session_id)
                if row:
                    row.captured_count += 1
        except Exception:
            self._increment_skipped(session_id)

    def _increment_skipped(self, session_id: int) -> None:
        with session_scope() as session:
            row = session.get(BrowserCaptureSession, session_id)
            if row:
                row.skipped_count += 1

    def _finish_session(self, session_id: int, status: str, error: str | None) -> None:
        with session_scope() as session:
            row = session.get(BrowserCaptureSession, session_id)
            if row:
                row.status = status
                row.ended_at = datetime.utcnow()
                row.error_message = error


def session_payload(row: BrowserCaptureSession) -> dict[str, Any]:
    return {
        "id": row.id,
        "shop_id": row.shop_id,
        "status": row.status,
        "start_url": row.start_url,
        "allowed_domains": json.loads(row.allowed_domains_json or "[]"),
        "browser_engine": row.browser_engine,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "ended_at": row.ended_at.isoformat() if row.ended_at else None,
        "captured_count": row.captured_count,
        "skipped_count": row.skipped_count,
        "error_message": row.error_message,
    }


def record_payload(row: BrowserNetworkRecord, *, include_body: bool = False) -> dict[str, Any]:
    result = {
        "id": row.id,
        "session_id": row.session_id,
        "shop_id": row.shop_id,
        "observed_at": row.observed_at.isoformat(),
        "method": row.method,
        "url": row.url,
        "query_keys": json.loads(row.query_keys_json or "[]"),
        "status_code": row.status_code,
        "content_type": row.content_type,
        "resource_type": row.resource_type,
        "category": row.category,
        "evidence": json.loads(row.evidence_json or "[]"),
        "body_bytes": row.body_bytes,
        "redacted_fields": row.redacted_fields,
        "capture_error": row.capture_error,
    }
    if include_body:
        result["body"] = json.loads(row.body_json) if row.body_json else None
    return result


def recent_sessions(shop_id: int, limit: int = 20) -> list[dict[str, Any]]:
    with session_scope() as session:
        rows = session.scalars(
            select(BrowserCaptureSession)
            .where(BrowserCaptureSession.shop_id == shop_id)
            .order_by(desc(BrowserCaptureSession.id))
            .limit(limit)
        ).all()
        return [session_payload(row) for row in rows]


browser_bridge_manager = BrowserBridgeManager()
