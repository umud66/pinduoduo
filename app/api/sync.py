from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, select

from app.db.database import session_scope
from app.db.models import Product, Shop, Sku, SyncJob
from app.db.sync_models import SyncCursor, SyncPreference
from app.services.pdd.runner import sync_runner

router = APIRouter(tags=["sync"])


class SyncPreferenceUpdate(BaseModel):
    auto_sync: bool
    interval_minutes: int = Field(default=30, ge=15, le=1440)


def _decode_stats(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        decoded = json.loads(value)
        return decoded if isinstance(decoded, dict) else {}
    except json.JSONDecodeError:
        return {}


def _job_payload(job: SyncJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "shop_id": job.shop_id,
        "job_type": job.job_type,
        "status": job.status,
        "stats": _decode_stats(job.stats_json),
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


@router.get("/sync/shops/{shop_id}/status")
def get_sync_status(shop_id: int) -> dict[str, Any]:
    with session_scope() as session:
        shop = session.get(Shop, shop_id)
        if shop is None:
            raise HTTPException(status_code=404, detail="店铺不存在")

        cursors = session.scalars(
            select(SyncCursor)
            .where(SyncCursor.shop_id == shop_id)
            .order_by(SyncCursor.resource)
        ).all()
        jobs = session.scalars(
            select(SyncJob)
            .where(SyncJob.shop_id == shop_id)
            .order_by(desc(SyncJob.id))
            .limit(12)
        ).all()
        pref = session.scalar(
            select(SyncPreference).where(SyncPreference.shop_id == shop_id)
        )
        product_count = session.query(Product).filter(Product.shop_id == shop_id).count()
        sku_count = (
            session.query(Sku)
            .join(Product, Sku.product_id == Product.id)
            .filter(Product.shop_id == shop_id)
            .count()
        )

        return {
            "shop_id": shop_id,
            "configured": bool(
                shop.client_id
                and shop.client_secret_encrypted
                and shop.access_token_encrypted
            ),
            "product_count": product_count,
            "sku_count": sku_count,
            "active": any(job.status in ("queued", "running") for job in jobs),
            "cursors": {
                cursor.resource: {
                    "last_synced_at": cursor.last_synced_at,
                    "last_synced_at_iso": (
                        datetime.fromtimestamp(cursor.last_synced_at).isoformat()
                        if cursor.last_synced_at
                        else None
                    ),
                }
                for cursor in cursors
            },
            "preference": {
                "auto_sync": bool(pref.auto_sync) if pref else False,
                "interval_minutes": pref.interval_minutes if pref else 30,
                "last_auto_sync_at": (
                    pref.last_auto_sync_at.isoformat()
                    if pref and pref.last_auto_sync_at
                    else None
                ),
            },
            "jobs": [_job_payload(job) for job in jobs],
        }


def _submit(shop_id: int, job_type: str, **kwargs: Any) -> dict[str, Any]:
    try:
        job_id = sync_runner.submit(shop_id, job_type, **kwargs)
        return {"accepted": True, "job_id": job_id, "job_type": job_type}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/sync/shops/{shop_id}/full", status_code=202)
def start_full_sync(
    shop_id: int,
    lookback_days: int = Query(default=30, ge=1, le=90),
) -> dict[str, Any]:
    return _submit(shop_id, "full", lookback_days=lookback_days)


@router.post("/sync/shops/{shop_id}/incremental", status_code=202)
def start_incremental_sync(shop_id: int) -> dict[str, Any]:
    return _submit(shop_id, "incremental")


@router.post("/sync/shops/{shop_id}/products", status_code=202)
def start_product_sync(shop_id: int) -> dict[str, Any]:
    return _submit(shop_id, "products")


@router.post("/sync/shops/{shop_id}/orders", status_code=202)
def start_order_sync(
    shop_id: int,
    lookback_days: int = Query(default=7, ge=1, le=30),
) -> dict[str, Any]:
    return _submit(shop_id, "orders", lookback_days=lookback_days)


@router.post("/sync/shops/{shop_id}/refunds", status_code=202)
def start_refund_sync(
    shop_id: int,
    lookback_days: int = Query(default=7, ge=1, le=30),
) -> dict[str, Any]:
    return _submit(shop_id, "refunds", lookback_days=lookback_days)


@router.get("/sync/jobs/{job_id}")
def get_sync_job(job_id: int) -> dict[str, Any]:
    with session_scope() as session:
        job = session.get(SyncJob, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="同步任务不存在")
        return _job_payload(job)


@router.put("/sync/shops/{shop_id}/preference")
def update_sync_preference(
    shop_id: int, payload: SyncPreferenceUpdate
) -> dict[str, Any]:
    with session_scope() as session:
        if session.get(Shop, shop_id) is None:
            raise HTTPException(status_code=404, detail="店铺不存在")
        pref = session.scalar(
            select(SyncPreference).where(SyncPreference.shop_id == shop_id)
        )
        if pref is None:
            pref = SyncPreference(shop_id=shop_id)
            session.add(pref)
        pref.auto_sync = payload.auto_sync
        pref.interval_minutes = payload.interval_minutes
        session.flush()
        return {
            "shop_id": shop_id,
            "auto_sync": pref.auto_sync,
            "interval_minutes": pref.interval_minutes,
        }
