from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.models import TimestampMixin


class OptimizationTask(TimestampMixin, Base):
    __tablename__ = "optimization_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), index=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.id", ondelete="CASCADE"), index=True)
    diagnosis_id: Mapped[int | None] = mapped_column(
        ForeignKey("diagnosis_results.id", ondelete="SET NULL"), nullable=True, index=True
    )
    issue_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    action_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="planned", nullable=False, index=True)
    action_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    baseline_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class OptimizationReview(TimestampMixin, Base):
    __tablename__ = "optimization_reviews"
    __table_args__ = (
        UniqueConstraint("task_id", "window_days", name="uq_optimization_review_task_window"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("optimization_tasks.id", ondelete="CASCADE"), index=True
    )
    window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    baseline_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    observed_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
