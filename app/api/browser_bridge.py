from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, select

from app.db.browser_models import BrowserCaptureSession, BrowserNetworkRecord
from app.db.database import session_scope
from app.services.browser_bridge.runner import (
    browser_bridge_manager,
    recent_sessions,
    record_payload,
    session_payload,
)

router = APIRouter(prefix="/browser-bridge", tags=["browser-bridge"])


class BrowserSessionCreate(BaseModel):
    shop_id: int = Field(gt=0)
    start_url: str = Field(min_length=8, max_length=2048)
    allowed_domains: list[str] = Field(default_factory=lambda: ["pinduoduo.com", "yangkeduo.com"])


@router.get("/status")
def get_status() -> dict[str, object]:
    return browser_bridge_manager.status()


@router.post("/sessions", status_code=202)
def start_session(payload: BrowserSessionCreate) -> dict[str, object]:
    try:
        session_id = browser_bridge_manager.start(
            shop_id=payload.shop_id,
            start_url=payload.start_url,
            allowed_domains=payload.allowed_domains,
        )
        return {"accepted": True, "session_id": session_id}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/sessions/stop")
def stop_session() -> dict[str, object]:
    return {"stopping": browser_bridge_manager.stop()}


@router.get("/shops/{shop_id}/sessions")
def get_sessions(shop_id: int, limit: int = Query(default=20, ge=1, le=100)) -> dict[str, object]:
    items = recent_sessions(shop_id, limit)
    return {"items": items, "total": len(items)}


@router.get("/sessions/{session_id}")
def get_session(session_id: int) -> dict[str, object]:
    with session_scope() as session:
        row = session.get(BrowserCaptureSession, session_id)
        if row is None:
            raise HTTPException(status_code=404, detail="浏览器采集会话不存在")
        return session_payload(row)


@router.get("/sessions/{session_id}/records")
def get_records(
    session_id: int,
    limit: int = Query(default=80, ge=1, le=300),
    category: str | None = None,
    include_body: bool = False,
) -> dict[str, object]:
    with session_scope() as session:
        if session.get(BrowserCaptureSession, session_id) is None:
            raise HTTPException(status_code=404, detail="浏览器采集会话不存在")
        stmt = select(BrowserNetworkRecord).where(BrowserNetworkRecord.session_id == session_id)
        if category and category != "all":
            stmt = stmt.where(BrowserNetworkRecord.category == category)
        rows = session.scalars(stmt.order_by(desc(BrowserNetworkRecord.id)).limit(limit)).all()
        return {
            "items": [record_payload(row, include_body=include_body) for row in rows],
            "total": len(rows),
        }
