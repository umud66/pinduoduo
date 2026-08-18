from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.db.database import session_scope
from app.db.optimization_models import OptimizationTask
from app.services.optimization import (
    cancel_task,
    complete_task,
    create_manual_task,
    create_task_from_diagnosis,
    list_tasks,
    refresh_shop_reviews,
    refresh_task_reviews,
    start_task,
    task_payload,
)

router = APIRouter(prefix="/optimization", tags=["optimization"])


class DiagnosisTaskCreate(BaseModel):
    issue_code: str | None = None
    action_index: int = Field(default=0, ge=0)
    title: str | None = Field(default=None, max_length=256)


class ManualTaskCreate(BaseModel):
    shop_id: int = Field(gt=0)
    sku_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=256)
    action: str = Field(min_length=1, max_length=2000)
    validation_metrics: list[str] = Field(default_factory=list)
    notes: str = Field(default="", max_length=4000)


class CompleteTask(BaseModel):
    execution_note: str = Field(default="", max_length=4000)


@router.get("/tasks")
def get_tasks(
    shop_id: int = Query(gt=0),
    status: str = "all",
) -> dict[str, object]:
    with session_scope() as session:
        items = list_tasks(session, shop_id=shop_id, status=status)
        return {"items": items, "total": len(items)}


@router.get("/tasks/{task_id}")
def get_task(task_id: int) -> dict[str, object]:
    with session_scope() as session:
        task = session.get(OptimizationTask, task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="优化任务不存在")
        return task_payload(session, task)


@router.post("/diagnoses/{diagnosis_id}/tasks")
def create_from_diagnosis(diagnosis_id: int, payload: DiagnosisTaskCreate) -> dict[str, object]:
    try:
        with session_scope() as session:
            task = create_task_from_diagnosis(
                session,
                diagnosis_id,
                issue_code=payload.issue_code,
                action_index=payload.action_index,
                title=payload.title,
            )
            return task_payload(session, task)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tasks")
def create_task(payload: ManualTaskCreate) -> dict[str, object]:
    try:
        with session_scope() as session:
            task = create_manual_task(
                session,
                shop_id=payload.shop_id,
                sku_id=payload.sku_id,
                title=payload.title,
                action=payload.action,
                validation_metrics=payload.validation_metrics,
                notes=payload.notes,
            )
            return task_payload(session, task)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/start")
def start(task_id: int) -> dict[str, object]:
    try:
        with session_scope() as session:
            task = start_task(session, task_id)
            return task_payload(session, task)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/complete")
def complete(task_id: int, payload: CompleteTask) -> dict[str, object]:
    try:
        with session_scope() as session:
            task = complete_task(session, task_id, execution_note=payload.execution_note)
            return task_payload(session, task)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/cancel")
def cancel(task_id: int) -> dict[str, object]:
    try:
        with session_scope() as session:
            task = cancel_task(session, task_id)
            return task_payload(session, task)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/reviews/refresh")
def refresh_reviews(task_id: int) -> dict[str, object]:
    try:
        with session_scope() as session:
            task = refresh_task_reviews(session, task_id)
            return task_payload(session, task)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/shops/{shop_id}/reviews/refresh")
def refresh_reviews_for_shop(shop_id: int) -> dict[str, int]:
    with session_scope() as session:
        return refresh_shop_reviews(session, shop_id)
