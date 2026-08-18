from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.models import TimestampMixin


class BrowserCaptureSession(TimestampMixin, Base):
    __tablename__ = "browser_capture_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="starting", index=True)
    start_url: Mapped[str] = mapped_column(Text, nullable=False)
    allowed_domains_json: Mapped[str] = mapped_column(Text, nullable=False)
    browser_engine: Mapped[str] = mapped_column(String(32), default="chromium", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    captured_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class BrowserNetworkRecord(TimestampMixin, Base):
    __tablename__ = "browser_network_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("browser_capture_sessions.id", ondelete="CASCADE"), index=True
    )
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    method: Mapped[str] = mapped_column(String(16), default="GET")
    url: Mapped[str] = mapped_column(Text, nullable=False)
    query_keys_json: Mapped[str] = mapped_column(Text, default="[]")
    status_code: Mapped[int] = mapped_column(Integer, default=0)
    content_type: Mapped[str | None] = mapped_column(String(256), nullable=True)
    resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    category: Mapped[str] = mapped_column(String(32), default="unknown", index=True)
    evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    body_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_bytes: Mapped[int] = mapped_column(Integer, default=0)
    redacted_fields: Mapped[int] = mapped_column(Integer, default=0)
    capture_error: Mapped[str | None] = mapped_column(String(256), nullable=True)
