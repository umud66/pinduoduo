from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.diagnosis.service import diagnose_latest_sku

router = APIRouter(tags=["diagnosis"])


@router.post("/diagnosis/skus/{sku_id}")
def run_sku_diagnosis(sku_id: int) -> dict[str, object]:
    try:
        return diagnose_latest_sku(sku_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
