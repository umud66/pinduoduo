from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.secrets import SecretStore
from app.db.database import session_scope
from app.db.models import ImportJob, Product, Shop, Sku, SkuDailyMetric
from app.services.importer.report_import import import_report
from app.services.importer.report_reader import preview_report

router = APIRouter(tags=["data"])
secret_store = SecretStore()


class ShopCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    client_id: str | None = None
    client_secret: str | None = None
    access_token: str | None = None


class ShopUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    client_id: str | None = None
    client_secret: str | None = None
    access_token: str | None = None
    enabled: bool | None = None


class ReportCommit(BaseModel):
    shop_id: int = Field(gt=0)
    stored_as: str = Field(min_length=1)


def _shop_payload(shop: Shop, *, product_count: int = 0, sku_count: int = 0, metric_count: int = 0) -> dict[str, object]:
    return {
        "id": shop.id,
        "name": shop.name,
        "platform": shop.platform,
        "enabled": shop.enabled,
        "client_id": shop.client_id,
        "has_client_secret": bool(shop.client_secret_encrypted),
        "has_access_token": bool(shop.access_token_encrypted),
        "pdd_configured": bool(shop.client_id and shop.client_secret_encrypted),
        "product_count": product_count,
        "sku_count": sku_count,
        "metric_count": metric_count,
    }


@router.get("/shops")
def list_shops() -> list[dict[str, object]]:
    with session_scope() as session:
        shops = session.scalars(select(Shop).order_by(Shop.id)).all()
        result: list[dict[str, object]] = []
        for shop in shops:
            product_count = session.scalar(
                select(func.count()).select_from(Product).where(Product.shop_id == shop.id)
            ) or 0
            sku_count = session.scalar(
                select(func.count())
                .select_from(Sku)
                .join(Product, Sku.product_id == Product.id)
                .where(Product.shop_id == shop.id)
            ) or 0
            metric_count = session.scalar(
                select(func.count()).select_from(SkuDailyMetric).where(SkuDailyMetric.shop_id == shop.id)
            ) or 0
            result.append(
                _shop_payload(
                    shop,
                    product_count=product_count,
                    sku_count=sku_count,
                    metric_count=metric_count,
                )
            )
        return result


@router.get("/shops/{shop_id}")
def get_shop(shop_id: int) -> dict[str, object]:
    with session_scope() as session:
        shop = session.get(Shop, shop_id)
        if shop is None:
            raise HTTPException(status_code=404, detail="店铺不存在")
        return _shop_payload(shop)


@router.post("/shops")
def create_shop(payload: ShopCreate) -> dict[str, object]:
    with session_scope() as session:
        shop = Shop(
            name=payload.name.strip(),
            client_id=(payload.client_id or "").strip() or None,
            client_secret_encrypted=secret_store.encrypt(payload.client_secret or "") or None,
            access_token_encrypted=secret_store.encrypt(payload.access_token or "") or None,
        )
        session.add(shop)
        session.flush()
        return _shop_payload(shop)


@router.put("/shops/{shop_id}")
def update_shop(shop_id: int, payload: ShopUpdate) -> dict[str, object]:
    with session_scope() as session:
        shop = session.get(Shop, shop_id)
        if shop is None:
            raise HTTPException(status_code=404, detail="店铺不存在")
        if payload.name is not None:
            shop.name = payload.name.strip()
        if payload.client_id is not None:
            shop.client_id = payload.client_id.strip() or None
        if payload.client_secret is not None and payload.client_secret.strip():
            shop.client_secret_encrypted = secret_store.encrypt(payload.client_secret.strip())
        if payload.access_token is not None and payload.access_token.strip():
            shop.access_token_encrypted = secret_store.encrypt(payload.access_token.strip())
        if payload.enabled is not None:
            shop.enabled = payload.enabled
        session.flush()
        return _shop_payload(shop)


@router.delete("/shops/{shop_id}")
def delete_shop(shop_id: int) -> dict[str, object]:
    with session_scope() as session:
        shop = session.get(Shop, shop_id)
        if shop is None:
            raise HTTPException(status_code=404, detail="店铺不存在")
        session.delete(shop)
        return {"ok": True}


def _save_upload(file: UploadFile) -> Path:
    settings = get_settings()
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".csv", ".xlsx", ".xlsm"}:
        raise HTTPException(status_code=400, detail="仅支持 CSV/XLSX/XLSM")
    target = settings.data_dir / "imports" / f"{uuid.uuid4().hex}{suffix}"
    with target.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    return target


@router.post("/reports/preview")
def preview_uploaded_report(file: UploadFile = File(...)) -> dict[str, object]:
    target = _save_upload(file)
    try:
        preview = preview_report(target)
        return {
            "stored_as": target.name,
            "original_filename": file.filename,
            "headers": preview.headers,
            "detected_fields": preview.detected_fields,
            "rows": preview.rows,
            "can_import": "date" in preview.detected_fields and "sku_id" in preview.detected_fields,
            "missing_required": [
                field for field in ("date", "sku_id") if field not in preview.detected_fields
            ],
        }
    except Exception as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/reports/import")
def commit_report(payload: ReportCommit) -> dict[str, object]:
    settings = get_settings()
    safe_name = Path(payload.stored_as).name
    if safe_name != payload.stored_as:
        raise HTTPException(status_code=400, detail="非法文件名")
    target = settings.data_dir / "imports" / safe_name
    if not target.exists():
        raise HTTPException(status_code=404, detail="待导入文件不存在，请重新选择报表")

    try:
        with session_scope() as session:
            job = ImportJob(shop_id=payload.shop_id, filename=safe_name, status="running")
            session.add(job)
            session.flush()
            try:
                preview = preview_report(target)
                job.detected_columns_json = json.dumps(preview.detected_fields, ensure_ascii=False)
                summary = import_report(session, shop_id=payload.shop_id, path=target)
                job.status = "success"
                job.report_type = "sku_daily_metric"
                session.flush()
                return {"ok": True, "job_id": job.id, "summary": summary.as_dict()}
            except Exception as exc:
                job.status = "failed"
                job.error_message = str(exc)
                raise
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/reports/upload-and-import")
def upload_and_import_report(
    shop_id: int = Form(...), file: UploadFile = File(...)
) -> dict[str, object]:
    target = _save_upload(file)
    try:
        with session_scope() as session:
            summary = import_report(session, shop_id=shop_id, path=target)
            return {"ok": True, "summary": summary.as_dict(), "stored_as": target.name}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
