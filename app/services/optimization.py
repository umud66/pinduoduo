from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any, Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import DiagnosisResult, Product, Sku, SkuDailyMetric
from app.db.optimization_models import OptimizationReview, OptimizationTask
from app.services.optimization_review import compare_review_snapshots, review_required_days
from app.services.trends import aggregate_points, metric_point_from_row

REVIEW_WINDOWS = (3, 7, 14)
ACTIVE_STATUSES = {"planned", "in_progress", "completed"}


def _safe_json(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _snapshot_from_rows(rows: Iterable[SkuDailyMetric]) -> dict[str, Any]:
    points = [metric_point_from_row(row) for row in rows]
    aggregate = aggregate_points(points)
    return {
        "days": aggregate.get("days", 0),
        "gmv": aggregate.get("avg_daily_gmv"),
        "sales_qty": aggregate.get("avg_daily_sales_qty"),
        "order_count": aggregate.get("avg_daily_order_count"),
        "ctr": aggregate.get("ctr"),
        "cvr": aggregate.get("cvr"),
        "refund_rate": aggregate.get("refund_rate"),
        "ad_roi": aggregate.get("ad_roi"),
        "avg_price": aggregate.get("avg_price"),
        "avg_stock": aggregate.get("avg_stock"),
    }


def _metric_rows(session: Session, sku_id: int, start: date, end: date) -> list[SkuDailyMetric]:
    if end < start:
        return []
    return list(
        session.scalars(
            select(SkuDailyMetric)
            .where(
                SkuDailyMetric.sku_id == sku_id,
                SkuDailyMetric.metric_date >= start,
                SkuDailyMetric.metric_date <= end,
            )
            .order_by(SkuDailyMetric.metric_date)
        ).all()
    )


def _task_action(task: OptimizationTask) -> dict[str, Any]:
    return _safe_json(task.action_json)


def _review_payload(review: OptimizationReview) -> dict[str, Any]:
    return {
        "id": review.id,
        "window_days": review.window_days,
        "due_date": review.due_date.isoformat(),
        "status": review.status,
        "baseline": _safe_json(review.baseline_json),
        "observed": _safe_json(review.observed_json),
        "result": _safe_json(review.result_json),
        "reviewed_at": review.reviewed_at.isoformat() if review.reviewed_at else None,
    }


def task_payload(session: Session, task: OptimizationTask) -> dict[str, Any]:
    sku = session.get(Sku, task.sku_id)
    product = session.get(Product, sku.product_id) if sku else None
    reviews = list(
        session.scalars(
            select(OptimizationReview)
            .where(OptimizationReview.task_id == task.id)
            .order_by(OptimizationReview.window_days)
        ).all()
    )
    next_review = next((item for item in reviews if item.status in {"pending", "insufficient_data"}), None)
    completed_reviews = [item for item in reviews if item.status == "completed"]
    latest_result = _safe_json(completed_reviews[-1].result_json) if completed_reviews else None
    return {
        "id": task.id,
        "shop_id": task.shop_id,
        "sku_id": task.sku_id,
        "diagnosis_id": task.diagnosis_id,
        "issue_code": task.issue_code,
        "action_index": task.action_index,
        "title": task.title,
        "source": task.source,
        "status": task.status,
        "action": _task_action(task),
        "baseline": _safe_json(task.baseline_json),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "cancelled_at": task.cancelled_at.isoformat() if task.cancelled_at else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        "sku": {
            "id": sku.id,
            "name": sku.sku_name or sku.platform_sku_id,
            "platform_sku_id": sku.platform_sku_id,
        }
        if sku
        else None,
        "product": {"id": product.id, "title": product.title} if product else None,
        "reviews": [_review_payload(item) for item in reviews],
        "next_review": _review_payload(next_review) if next_review else None,
        "latest_outcome": latest_result.get("outcome") if latest_result else None,
    }


def _resolve_issue(diagnosis_payload: dict[str, Any], issue_code: str | None) -> dict[str, Any]:
    issues = [item for item in diagnosis_payload.get("issues", []) if isinstance(item, dict)]
    if not issues:
        raise ValueError("该诊断没有可创建任务的问题")
    if issue_code:
        issue = next((item for item in issues if item.get("code") == issue_code), None)
        if issue is None:
            raise ValueError("指定的诊断问题不存在")
        return issue
    return issues[0]


def create_task_from_diagnosis(
    session: Session,
    diagnosis_id: int,
    *,
    issue_code: str | None = None,
    action_index: int = 0,
    title: str | None = None,
) -> OptimizationTask:
    diagnosis = session.get(DiagnosisResult, diagnosis_id)
    if diagnosis is None:
        raise LookupError("诊断记录不存在")
    sku = session.get(Sku, diagnosis.sku_id)
    if sku is None:
        raise LookupError("SKU 不存在")
    product = session.get(Product, sku.product_id)
    if product is None:
        raise LookupError("商品不存在")

    payload = _safe_json(diagnosis.diagnosis_json)
    issue = _resolve_issue(payload, issue_code)
    actions = [str(item) for item in issue.get("actions", []) if str(item).strip()]
    if not actions:
        raise ValueError("该问题没有可执行动作")
    if action_index < 0 or action_index >= len(actions):
        raise ValueError("动作序号超出范围")
    selected_action = actions[action_index]
    validation_metrics = [str(item) for item in issue.get("validation_metrics", [])]

    task = OptimizationTask(
        shop_id=product.shop_id,
        sku_id=sku.id,
        diagnosis_id=diagnosis.id,
        issue_code=str(issue.get("code") or "") or None,
        action_index=action_index,
        title=(title or f"{issue.get('title') or 'SKU 优化'}：{selected_action}")[:256],
        source="diagnosis",
        status="planned",
        action_json=_dump(
            {
                "action": selected_action,
                "issue_title": issue.get("title"),
                "reason": issue.get("reason"),
                "validation_metrics": validation_metrics,
                "diagnosis_priority": issue.get("priority_score"),
                "estimated_loss": issue.get("estimated_loss"),
                "execution_note": "",
            }
        ),
    )
    session.add(task)
    session.flush()
    return task


def create_manual_task(
    session: Session,
    *,
    shop_id: int,
    sku_id: int,
    title: str,
    action: str,
    validation_metrics: list[str],
    notes: str = "",
) -> OptimizationTask:
    sku = session.get(Sku, sku_id)
    if sku is None:
        raise LookupError("SKU 不存在")
    product = session.get(Product, sku.product_id)
    if product is None or product.shop_id != shop_id:
        raise ValueError("SKU 不属于当前店铺")
    task = OptimizationTask(
        shop_id=shop_id,
        sku_id=sku_id,
        title=title.strip()[:256],
        source="manual",
        status="planned",
        action_json=_dump(
            {
                "action": action.strip(),
                "validation_metrics": [item.strip() for item in validation_metrics if item.strip()],
                "notes": notes.strip(),
                "execution_note": "",
            }
        ),
    )
    session.add(task)
    session.flush()
    return task


def _baseline_snapshot(session: Session, task: OptimizationTask, action_date: date) -> dict[str, Any]:
    rows = _metric_rows(session, task.sku_id, action_date - timedelta(days=7), action_date - timedelta(days=1))
    return _snapshot_from_rows(rows)


def start_task(session: Session, task_id: int, *, started_at: datetime | None = None) -> OptimizationTask:
    task = session.get(OptimizationTask, task_id)
    if task is None:
        raise LookupError("优化任务不存在")
    if task.status == "cancelled":
        raise ValueError("已取消任务不能开始")
    if task.status == "completed":
        return task
    if task.started_at is not None:
        return task

    started = started_at or datetime.utcnow()
    action_date = started.date()
    baseline = _baseline_snapshot(session, task, action_date)
    task.started_at = started
    task.status = "in_progress"
    task.baseline_json = _dump(baseline)

    for window_days in REVIEW_WINDOWS:
        session.add(
            OptimizationReview(
                task_id=task.id,
                window_days=window_days,
                due_date=action_date + timedelta(days=window_days),
                status="pending",
                baseline_json=_dump(baseline),
            )
        )
    session.flush()
    return task


def complete_task(
    session: Session,
    task_id: int,
    *,
    execution_note: str = "",
    completed_at: datetime | None = None,
) -> OptimizationTask:
    task = session.get(OptimizationTask, task_id)
    if task is None:
        raise LookupError("优化任务不存在")
    if task.status == "cancelled":
        raise ValueError("已取消任务不能完成")
    if task.status == "completed":
        return task
    if task.started_at is None:
        start_task(session, task_id, started_at=completed_at)
        task = session.get(OptimizationTask, task_id)
        assert task is not None
    task.status = "completed"
    task.completed_at = completed_at or datetime.utcnow()
    action = _task_action(task)
    action["execution_note"] = execution_note.strip()
    task.action_json = _dump(action)
    session.flush()
    return task


def cancel_task(session: Session, task_id: int) -> OptimizationTask:
    task = session.get(OptimizationTask, task_id)
    if task is None:
        raise LookupError("优化任务不存在")
    if task.status == "completed":
        raise ValueError("已完成任务不能取消")
    task.status = "cancelled"
    task.cancelled_at = datetime.utcnow()
    reviews = session.scalars(
        select(OptimizationReview).where(OptimizationReview.task_id == task.id)
    ).all()
    for review in reviews:
        if review.status != "completed":
            review.status = "skipped"
    session.flush()
    return task


def refresh_task_reviews(session: Session, task_id: int) -> OptimizationTask:
    task = session.get(OptimizationTask, task_id)
    if task is None:
        raise LookupError("优化任务不存在")
    if task.started_at is None or task.status == "cancelled":
        return task

    action_date = task.started_at.date()
    action = _task_action(task)
    validation_metrics = [str(item) for item in action.get("validation_metrics", [])]
    latest_metric_date = session.scalar(
        select(func.max(SkuDailyMetric.metric_date)).where(SkuDailyMetric.sku_id == task.sku_id)
    )
    reviews = session.scalars(
        select(OptimizationReview)
        .where(OptimizationReview.task_id == task.id)
        .order_by(OptimizationReview.window_days)
    ).all()
    for review in reviews:
        if review.status == "skipped":
            continue
        if latest_metric_date is None or latest_metric_date < review.due_date:
            review.status = "pending"
            continue
        rows = _metric_rows(
            session,
            task.sku_id,
            action_date + timedelta(days=1),
            review.due_date,
        )
        observed = _snapshot_from_rows(rows)
        review.observed_json = _dump(observed)
        required = review_required_days(review.window_days)
        if int(observed.get("days") or 0) < required:
            review.status = "insufficient_data"
            review.result_json = _dump(
                {
                    "outcome": "insufficient_data",
                    "required_days": required,
                    "observed_days": int(observed.get("days") or 0),
                    "interpretation": "已到复盘窗口，但有效数据覆盖不足，暂不判断动作效果。",
                }
            )
            review.reviewed_at = datetime.utcnow()
            continue
        baseline = _safe_json(review.baseline_json)
        result = compare_review_snapshots(baseline, observed, validation_metrics)
        result["required_days"] = required
        result["observed_days"] = int(observed.get("days") or 0)
        review.result_json = _dump(result)
        review.status = "completed"
        review.reviewed_at = datetime.utcnow()
    session.flush()
    return task


def refresh_shop_reviews(session: Session, shop_id: int) -> dict[str, int]:
    task_ids = list(
        session.scalars(
            select(OptimizationTask.id).where(
                OptimizationTask.shop_id == shop_id,
                OptimizationTask.status.in_(ACTIVE_STATUSES),
                OptimizationTask.started_at.is_not(None),
            )
        ).all()
    )
    refreshed = 0
    completed = 0
    for task_id in task_ids:
        task = refresh_task_reviews(session, int(task_id))
        refreshed += 1
        completed += sum(
            1
            for review in session.scalars(
                select(OptimizationReview).where(OptimizationReview.task_id == task.id)
            ).all()
            if review.status == "completed"
        )
    return {"tasks_refreshed": refreshed, "completed_reviews": completed}


def list_tasks(
    session: Session,
    *,
    shop_id: int,
    status: str = "all",
) -> list[dict[str, Any]]:
    statement = select(OptimizationTask).where(OptimizationTask.shop_id == shop_id)
    if status != "all":
        statement = statement.where(OptimizationTask.status == status)
    tasks = session.scalars(statement.order_by(OptimizationTask.updated_at.desc(), OptimizationTask.id.desc())).all()
    return [task_payload(session, task) for task in tasks]
