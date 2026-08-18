from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.db.database import session_scope
from app.services.insights import shop_trend_overview, sku_insights
from app.services.workspace import bootstrap_status, dashboard_summary, list_skus, seed_demo_data, sku_detail

router = APIRouter(tags=["workspace"])


@router.get("/workspace/bootstrap")
def get_bootstrap_status() -> dict[str, object]:
    with session_scope() as session:
        return bootstrap_status(session)


@router.get("/dashboard")
def get_dashboard(shop_id: int = Query(gt=0)) -> dict[str, object]:
    try:
        with session_scope() as session:
            return dashboard_summary(session, shop_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/skus")
def get_skus(
    shop_id: int = Query(gt=0),
    q: str = "",
    severity: str = "all",
) -> dict[str, object]:
    with session_scope() as session:
        items = list_skus(session, shop_id=shop_id, query=q, severity=severity)
        return {"items": items, "total": len(items)}


@router.get("/skus/{sku_id}")
def get_sku(sku_id: int) -> dict[str, object]:
    try:
        with session_scope() as session:
            return sku_detail(session, sku_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/skus/{sku_id}/insights")
def get_sku_insights(sku_id: int) -> dict[str, object]:
    try:
        with session_scope() as session:
            return sku_insights(session, sku_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/shops/{shop_id}/trend-overview")
def get_shop_trend_overview(
    shop_id: int,
    limit: int = Query(default=10, ge=1, le=50),
) -> dict[str, object]:
    with session_scope() as session:
        return shop_trend_overview(session, shop_id, limit=limit)


@router.post("/workspace/demo")
def create_demo_data(shop_id: int = Query(gt=0)) -> dict[str, object]:
    try:
        with session_scope() as session:
            return seed_demo_data(session, shop_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
