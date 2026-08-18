from __future__ import annotations

import json
from collections import defaultdict
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import DiagnosisResult, Product, Sku, SkuDailyMetric
from app.services.trends import (
    MetricPoint,
    build_30d_trend,
    build_issue_persistence,
    build_peer_comparison,
    build_window_comparison,
    metric_point_from_row,
)


def _percent_text(value: float | None) -> str:
    if value is None:
        return "数据不足"
    return f"{abs(value) * 100:.1f}%"


def _safe_json(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _current_issue_codes(diagnosis: DiagnosisResult | None) -> list[str]:
    payload = _safe_json(diagnosis.diagnosis_json if diagnosis else None)
    return [
        str(issue.get("code"))
        for issue in payload.get("issues", [])
        if isinstance(issue, dict) and issue.get("code")
    ]


def _diagnosis_history(rows: list[DiagnosisResult]) -> list[tuple[Any, set[str]]]:
    result = []
    for row in rows:
        payload = _safe_json(row.diagnosis_json)
        codes = {
            str(issue.get("code"))
            for issue in payload.get("issues", [])
            if isinstance(issue, dict) and issue.get("code")
        }
        result.append((row.period_end, codes))
    return result


def _summary(window: dict[str, Any], peer: dict[str, Any], persistence: dict[str, Any]) -> list[str]:
    messages: list[str] = []
    gmv_change = ((window.get("week_over_week") or {}).get("gmv") or {}).get("change")
    if gmv_change is not None:
        if gmv_change <= -0.08:
            messages.append(f"近 7 日日均 GMV 较前 7 日下降 {_percent_text(gmv_change)}")
        elif gmv_change >= 0.08:
            messages.append(f"近 7 日日均 GMV 较前 7 日增长 {_percent_text(gmv_change)}")
        else:
            messages.append("近 7 日日均 GMV 与前 7 日基本持平")

    target = peer.get("target") or {}
    if target and peer.get("peer_count", 0) > 1:
        messages.append(
            f"同商品 {peer['peer_count']} 个 SKU 中，近 7 日 GMV 排名第 {target.get('rank', '—')}"
        )

    days = int(persistence.get("max_consecutive_days") or 0)
    if days >= 2:
        messages.append(f"当前问题最长已连续出现 {days} 天")
    return messages


def sku_insights(session: Session, sku_id: int) -> dict[str, Any]:
    sku = session.get(Sku, sku_id)
    if sku is None:
        raise LookupError("SKU 不存在")
    product = session.get(Product, sku.product_id)
    if product is None:
        raise LookupError("商品不存在")

    metric_rows = session.scalars(
        select(SkuDailyMetric)
        .where(SkuDailyMetric.sku_id == sku_id)
        .order_by(SkuDailyMetric.metric_date.desc())
        .limit(30)
    ).all()
    points = [metric_point_from_row(row) for row in reversed(metric_rows)]
    window = build_window_comparison(points)
    trend_30d = build_30d_trend(points)

    latest_date = max((point.metric_date for point in points), default=None)
    peer_map: dict[int, list[MetricPoint]] = defaultdict(list)
    peer_names: dict[int, str] = {}
    if latest_date is not None:
        peer_skus = session.scalars(
            select(Sku).where(Sku.product_id == product.id).order_by(Sku.id)
        ).all()
        peer_names = {item.id: item.sku_name or item.platform_sku_id for item in peer_skus}
        peer_ids = list(peer_names)
        if peer_ids:
            peer_rows = session.scalars(
                select(SkuDailyMetric)
                .where(
                    SkuDailyMetric.sku_id.in_(peer_ids),
                    SkuDailyMetric.metric_date >= latest_date - timedelta(days=6),
                    SkuDailyMetric.metric_date <= latest_date,
                )
                .order_by(SkuDailyMetric.metric_date)
            ).all()
            for row in peer_rows:
                peer_map[row.sku_id].append(metric_point_from_row(row))
        for peer_id in peer_ids:
            peer_map.setdefault(peer_id, [])

    peer = build_peer_comparison(sku_id, peer_map, names=peer_names)

    diagnoses = session.scalars(
        select(DiagnosisResult)
        .where(DiagnosisResult.sku_id == sku_id)
        .order_by(DiagnosisResult.period_end.desc(), DiagnosisResult.id.desc())
        .limit(30)
    ).all()
    current_diagnosis = diagnoses[0] if diagnoses else None
    persistence = build_issue_persistence(
        _current_issue_codes(current_diagnosis),
        _diagnosis_history(list(diagnoses)),
    )

    return {
        "sku_id": sku.id,
        "product_id": product.id,
        "latest_date": latest_date.isoformat() if latest_date else None,
        "window_comparison": window,
        "trend_30d": trend_30d,
        "peer_comparison": peer,
        "persistence": persistence,
        "summary": _summary(window, peer, persistence),
        "data_quality": {
            "metric_days": len(points),
            "has_two_full_weeks": (
                window.get("window_coverage", {}).get("recent_7_days") == 7
                and window.get("window_coverage", {}).get("prior_7_days") == 7
            ),
            "peer_count": peer.get("peer_count", 0),
            "diagnosis_history_records": len(diagnoses),
        },
    }


def shop_trend_overview(session: Session, shop_id: int, *, limit: int = 10) -> dict[str, Any]:
    latest_date = session.scalar(
        select(func.max(SkuDailyMetric.metric_date)).where(SkuDailyMetric.shop_id == shop_id)
    )
    if latest_date is None:
        return {
            "latest_date": None,
            "summary": {"tracked": 0, "down": 0, "up": 0, "flat": 0, "unknown": 0},
            "top_decliners": [],
        }

    rows = session.scalars(
        select(SkuDailyMetric)
        .where(
            SkuDailyMetric.shop_id == shop_id,
            SkuDailyMetric.metric_date >= latest_date - timedelta(days=13),
            SkuDailyMetric.metric_date <= latest_date,
        )
        .order_by(SkuDailyMetric.sku_id, SkuDailyMetric.metric_date)
    ).all()
    grouped: dict[int, list[MetricPoint]] = defaultdict(list)
    for row in rows:
        grouped[row.sku_id].append(metric_point_from_row(row))

    sku_pairs = session.execute(
        select(Sku, Product)
        .join(Product, Sku.product_id == Product.id)
        .where(Product.shop_id == shop_id)
    ).all()
    metadata = {
        sku.id: {
            "sku_name": sku.sku_name or sku.platform_sku_id,
            "product_title": product.title,
            "image_url": sku.image_url or product.main_image,
        }
        for sku, product in sku_pairs
    }

    summary = {"tracked": 0, "down": 0, "up": 0, "flat": 0, "unknown": 0}
    items: list[dict[str, Any]] = []
    for sku_id, meta in metadata.items():
        comparison = build_window_comparison(grouped.get(sku_id, []))
        direction = str(comparison.get("trend_direction") or "unknown")
        summary["tracked"] += 1
        summary[direction if direction in summary else "unknown"] += 1
        gmv = (comparison.get("week_over_week") or {}).get("gmv") or {}
        sales = (comparison.get("week_over_week") or {}).get("sales_qty") or {}
        coverage = comparison.get("window_coverage") or {}
        items.append(
            {
                "sku_id": sku_id,
                **meta,
                "direction": direction,
                "gmv_change": gmv.get("change"),
                "sales_change": sales.get("change"),
                "recent_daily_gmv": gmv.get("current"),
                "prior_daily_gmv": gmv.get("baseline"),
                "recent_days": coverage.get("recent_7_days", 0),
                "prior_days": coverage.get("prior_7_days", 0),
            }
        )

    def decline_key(item: dict[str, Any]) -> tuple[int, float, float]:
        full = int(item["recent_days"] >= 3 and item["prior_days"] >= 3)
        change = item["gmv_change"] if item["gmv_change"] is not None else 999.0
        scale = -(float(item["prior_daily_gmv"] or 0))
        return (-full, change, scale)

    decliners = [item for item in items if item["direction"] == "down"]
    decliners.sort(key=decline_key)
    return {
        "latest_date": latest_date.isoformat(),
        "summary": summary,
        "top_decliners": decliners[:limit],
    }
