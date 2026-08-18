from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.config import get_settings
from app.db.database import session_scope
from app.db.models import Shop
from app.services.importer.report_reader import preview_report

router = APIRouter(tags=["data"])


class ShopCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    client_id: str | None = None


@router.get("/shops")
def list_shops() -> list[dict[str, object]]:
    with session_scope() as session:
        shops = session.scalars(select(Shop).order_by(Shop.id)).all()
        return [
            {"id": shop.id, "name": shop.name, "platform": shop.platform, "enabled": shop.enabled}
            for shop in shops
        ]


@router.post("/shops")
def create_shop(payload: ShopCreate) -> dict[str, object]:
    with session_scope() as session:
        shop = Shop(name=payload.name, client_id=payload.client_id)
        session.add(shop)
        session.flush()
        return {"id": shop.id, "name": shop.name}


@router.post("/reports/preview")
def preview_uploaded_report(file: UploadFile = File(...)) -> dict[str, object]:
    settings = get_settings()
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".csv", ".xlsx", ".xlsm"}:
        raise HTTPException(status_code=400, detail="仅支持 CSV/XLSX/XLSM")

    target = settings.data_dir / "imports" / f"{uuid.uuid4().hex}{suffix}"
    with target.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    try:
        preview = preview_report(target)
        return {
            "stored_as": target.name,
            "headers": preview.headers,
            "detected_fields": preview.detected_fields,
            "rows": preview.rows,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
